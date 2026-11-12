"""A robust agent loop: every way a run can stop, and every way a step can fail.

Stopping conditions (2.4):  final answer, max steps, wall-clock timeout,
token and cost budgets, repeated identical calls (no progress), a reply cut
off at max_tokens, and a refusal.

Error handling (2.5):  tool exceptions, invalid or missing arguments, unknown
tool names, arguments that were not valid JSON, transient API errors (retried
with exponential backoff), and oversized tool output.

    python main.py                     # from this folder
    python 02-robust-loop/main.py      # from examples/

Read alongside docs/02-the-agent-loop/02.4-stopping-conditions.md and 02.5-handling-errors-in-the-loop.md.
"""

from __future__ import annotations

import importlib
import json
import random
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolCall, Usage, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- limits and results


@dataclass
class Limits:
    """Every limit the loop enforces. The defaults suit a small interactive agent."""

    max_steps: int = 10  # model calls per run
    max_seconds: float = 120.0  # wall-clock time per run
    max_total_tokens: int = 200_000  # input + output tokens across the run
    max_cost_usd: float = 1.00  # same budget in dollars
    max_identical_calls: int = 2  # the same tool with the same arguments, more than this = no progress
    max_output_tokens: int = 4_000  # max_tokens for each reply
    max_truncation_retries: int = 1  # retries with a bigger max_tokens after a cut-off reply
    max_api_retries: int = 3  # retries for transient API errors (on top of the SDK's own retries)
    max_tool_output_chars: int = 4_000  # longer tool output is truncated before the model sees it
    # Claude Opus 5.5 list prices, USD per million tokens (November 2026). Change these for your model.
    input_price_per_mtok: float = 4.00
    output_price_per_mtok: float = 20.00


@dataclass
class RunResult:
    answer: str | None
    stopped_because: str  # final_answer | max_steps | timeout | token_budget | cost_budget | no_progress | max_tokens | refusal | api_error
    steps: int
    usage: Usage
    cost_usd: float
    log: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- tools, with input validation


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]

    @property
    def spec(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def validate_args(schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    """Check arguments against a flat JSON Schema. Returns a list of problems (empty = valid).

    Covers what tool schemas use most: required, types, enum and additionalProperties.
    For nested schemas use a full validator such as pydantic (see examples/03-tool-design).
    """
    props: dict[str, Any] = schema.get("properties", {})
    problems = [f"missing required argument '{name}'" for name in schema.get("required", []) if name not in args]
    for name, value in args.items():
        if name not in props:
            if schema.get("additionalProperties") is False:
                problems.append(f"unexpected argument '{name}' (allowed: {', '.join(props) or 'none'})")
            continue
        expected = props[name].get("type")
        ok_types = _JSON_TYPES.get(expected, (object,))
        if not isinstance(value, ok_types) or (expected in ("integer", "number") and isinstance(value, bool)):
            problems.append(f"'{name}' must be a {expected}, got {type(value).__name__} {value!r}")
        elif "enum" in props[name] and value not in props[name]["enum"]:
            problems.append(f"'{name}' must be one of {props[name]['enum']}, got {value!r}")
    return problems


def execute_tool(call: ToolCall, tools: dict[str, Tool], max_chars: int) -> tuple[str, bool]:
    """Run one tool call and return (content, is_error). Never raises: every failure becomes a message."""
    if call.error:  # the provider sent arguments we could not parse (see ToolCall.error)
        return f"Your arguments for {call.name} were not valid JSON ({call.error}). Send the call again.", True
    tool = tools.get(call.name)
    if tool is None:
        return f"Unknown tool '{call.name}'. Available tools: {', '.join(tools)}.", True
    problems = validate_args(tool.input_schema, call.arguments)
    if problems:
        return f"Invalid arguments for {call.name}: {'; '.join(problems)}. Fix them and call again.", True
    try:
        output = str(tool.fn(**call.arguments))
    except Exception as exc:  # the tool's own bug or failure
        return f"{call.name} failed: {type(exc).__name__}: {exc}", True
    if len(output) > max_chars:
        output = output[:max_chars] + f"\n[truncated: showing {max_chars} of {len(output)} characters]"
    return output, False


# --------------------------------------------------------------------------- transient API errors


class TransientError(Exception):
    """Stand-in for a temporary API failure in this demo (like a 429 or 529)."""

    def __init__(self, message: str, status_code: int = 529) -> None:
        super().__init__(message)
        self.status_code = status_code


RETRYABLE_STATUS = {408, 409, 429}  # plus every 5xx, including Anthropic's 529 "overloaded"


def _connection_errors() -> tuple[type[BaseException], ...]:
    """Network errors from the standard library and from whichever SDKs are installed."""
    errors: list[type[BaseException]] = [ConnectionError, TimeoutError]
    for module in ("anthropic", "openai"):
        try:
            errors.append(importlib.import_module(module).APIConnectionError)  # includes APITimeoutError
        except (ImportError, AttributeError):
            pass
    return tuple(errors)


CONNECTION_ERRORS = _connection_errors()


def is_transient(exc: BaseException) -> bool:
    """True for errors worth retrying: rate limits, overload, server errors, timeouts, dropped connections."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status in RETRYABLE_STATUS or status >= 500
    return isinstance(exc, CONNECTION_ERRORS)


def call_with_retries(
    fn: Callable[[], LLMResponse],
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    log: list[str] | None = None,
) -> LLMResponse:
    """Call fn(); on a transient error wait (exponential backoff with jitter) and try again."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if not is_transient(exc) or attempt == max_retries:
                raise  # permanent (400, 401, 404...) or out of retries: let the caller decide
            delay = random.uniform(0, min(max_delay, base_delay * 2**attempt))  # "full jitter"
            if log is not None:
                log.append(f"API call failed with a transient error ({exc}); "
                           f"retry {attempt + 1}/{max_retries} after {delay:.1f}s")
            sleep(delay)
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- the loop


def run_agent(
    llm: LLM,
    goal: str,
    tools: list[Tool],
    *,
    system: str = "",
    limits: Limits | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> RunResult:
    """Run the agent until it answers or a limit stops it. Never raises for model or tool problems."""
    limits = limits or Limits()
    registry = {t.name: t for t in tools}
    specs = [t.spec for t in tools]
    messages: list[Message] = [user(goal)]
    usage, log, seen = Usage(), [], Counter()
    started, max_tokens, truncation_retries, step = clock(), limits.max_output_tokens, 0, 0

    def cost() -> float:
        return (usage.input_tokens * limits.input_price_per_mtok
                + usage.output_tokens * limits.output_price_per_mtok) / 1_000_000

    def stop(reason: str, answer: str | None = None) -> RunResult:
        log.append(f"stop: {reason}")
        return RunResult(answer, reason, step, usage, round(cost(), 6), log)

    while step < limits.max_steps:
        # Checks BEFORE spending more: time and money.
        if clock() - started > limits.max_seconds:
            return stop("timeout")
        if usage.input_tokens + usage.output_tokens >= limits.max_total_tokens:
            return stop("token_budget")
        if cost() >= limits.max_cost_usd:
            return stop("cost_budget")

        step += 1
        try:
            reply = call_with_retries(
                lambda: llm.chat(messages, system=system, tools=specs, max_tokens=max_tokens),
                max_retries=limits.max_api_retries, sleep=sleep, log=log,
            )
        except Exception as exc:
            log.append(f"step {step}: API error: {type(exc).__name__}: {exc}")
            return stop("api_error")
        usage = Usage(usage.input_tokens + reply.usage.input_tokens, usage.output_tokens + reply.usage.output_tokens)

        if reply.stop_reason == "refusal":  # never run tools from a refused turn
            return stop("refusal", reply.text or None)
        if reply.stop_reason == "max_tokens":  # cut off: text incomplete, tool arguments may be broken
            if truncation_retries < limits.max_truncation_retries:
                truncation_retries += 1
                max_tokens *= 2
                log.append(f"step {step}: reply cut off at max_tokens; retrying with max_tokens={max_tokens}")
                continue  # the truncated reply is NOT added to the history
            return stop("max_tokens", reply.text or None)

        messages.append(reply.to_message())
        if not reply.tool_calls:
            log.append(f"step {step}: final answer")
            return stop("final_answer", reply.text)

        for call in reply.tool_calls:
            key = (call.name, json.dumps(call.arguments, sort_keys=True))
            seen[key] += 1
            if seen[key] > limits.max_identical_calls:
                log.append(f"step {step}: {call.name}({call.arguments}) repeated with no progress")
                return stop("no_progress")
            content, is_error = execute_tool(call, registry, limits.max_tool_output_chars)
            log.append(f"step {step}: {call.name}({call.arguments}) -> {'ERROR ' if is_error else ''}{content}")
            messages.append(tool_result(call.id, content, is_error=is_error))
    return stop("max_steps")


# --------------------------------------------------------------------------- demo

RATES = {("EUR", "USD"): 1.08, ("GBP", "USD"): 1.27}


def get_rate(base: str, quote: str) -> str:
    """Exchange rate from base to quote currency (fake data)."""
    if (base, quote) not in RATES:
        raise LookupError(f"no rate for {base}->{quote}; supported pairs: EUR->USD, GBP->USD")
    return str(RATES[(base, quote)])


def multiply(a: float, b: float) -> str:
    return str(round(a * b, 2))


TOOLS = [
    Tool("get_rate", "Get today's exchange rate from one currency to another, e.g. base='EUR', quote='USD'.",
         {"type": "object",
          "properties": {"base": {"type": "string", "enum": ["EUR", "GBP", "USD"]},
                         "quote": {"type": "string", "enum": ["EUR", "GBP", "USD"]}},
          "required": ["base", "quote"], "additionalProperties": False},
         get_rate),
    Tool("multiply", "Multiply two numbers.",
         {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
          "required": ["a", "b"], "additionalProperties": False},
         multiply),
]
GOAL = "How many US dollars is 250 euros today?"


class FlakyLLM(LLM):
    """Wraps another LLM and fails the first `failures` calls with a transient error."""

    provider = "flaky"

    def __init__(self, inner: LLM, failures: int = 1) -> None:
        self.inner, self.failures, self.model = inner, failures, getattr(inner, "model", "")

    def chat(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        if self.failures > 0:
            self.failures -= 1
            raise TransientError("529 overloaded_error")
        return self.inner.chat(messages, **kwargs)


BAD_JSON = LLMResponse(  # what the wrapper returns when a provider sends arguments that are not valid JSON
    tool_calls=[ToolCall(id="call_bad_json", name="get_rate", arguments={},
                         error="Invalid JSON arguments: Expecting ',' delimiter: line 1 column 16 (char 15)")],
    stop_reason="tool_use",
)
ERRORS_SCRIPT = [
    MockLLM.tool_call("get_rate", {"base": "EUR"}),  # missing argument
    MockLLM.tool_call("get_exchange_rate", {"base": "EUR", "quote": "USD"}),  # wrong tool name
    BAD_JSON,  # unparseable arguments
    MockLLM.tool_call("get_rate", {"base": "USD", "quote": "EUR"}),  # the tool itself raises
    MockLLM.tool_call("get_rate", {"base": "EUR", "quote": "USD"}),
    MockLLM.tool_call("multiply", {"a": 250, "b": 1.08}),
    "250 euros is about 270 US dollars today (rate 1.08).",
]


def fake_clock(seconds_per_call: float) -> Callable[[], float]:
    """A clock that jumps forward on every reading, so a timeout can be shown instantly."""
    now = [0.0]

    def clock() -> float:
        now[0] += seconds_per_call
        return now[0]

    return clock


def scenario_scripts() -> dict[str, tuple[list[Any], Limits, Callable[[], float]]]:
    """One short scripted run per stopping condition: (script, limits, clock)."""
    loop_forever = [MockLLM.tool_call("get_rate", {"base": "GBP", "quote": "USD"})] * 10
    truncated = LLMResponse(text="250 euros is about", stop_reason="max_tokens")
    busy = [MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(10)]
    real = time.monotonic
    return {
        "answers": (["250 euros is about 270 US dollars."], Limits(), real),
        "keeps calling tools": (busy, Limits(max_steps=3), real),
        "slow tools": (busy, Limits(max_seconds=120), fake_clock(50)),
        "token budget": (busy, Limits(max_total_tokens=100), real),
        "cost budget": (busy, Limits(max_cost_usd=0.0002), real),
        "repeats itself": (loop_forever, Limits(), real),
        "cut off once": ([truncated, "250 euros is about 270 US dollars."], Limits(), real),
        "cut off twice": ([truncated, truncated], Limits(), real),
        "refuses": ([LLMResponse(text="I can't help with that.", stop_reason="refusal")], Limits(), real),
    }


def main() -> None:
    print(f"Goal: {GOAL}\n\n1) A run that hits five different errors and still finishes\n")
    random.seed(7)  # the backoff jitter is random; fix it so the demo output is repeatable
    llm = FlakyLLM(get_llm(mock_responses=ERRORS_SCRIPT), failures=1)
    result = run_agent(llm, GOAL, TOOLS, sleep=lambda s: None)  # no real waiting in the demo
    print("\n".join(f"   {line}" for line in result.log))
    print(f"\n   Answer: {result.answer}")
    print(f"   Tokens: {result.usage.input_tokens} in / {result.usage.output_tokens} out (MockLLM estimates)")

    print("\n2) Why each run stopped\n")
    print(f"   {'scenario':<20} {'stopped_because':<16} steps")
    for name, (script, limits, clock) in scenario_scripts().items():
        r = run_agent(MockLLM(script), GOAL, TOOLS, limits=limits, clock=clock)
        print(f"   {name:<20} {r.stopped_because:<16} {r.steps}")


if __name__ == "__main__":
    main()
