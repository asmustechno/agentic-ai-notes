"""Structured JSON logs for every tool call, with a run ID, redaction and sizes instead of payloads.

    python main.py                          # from this folder
    python 14-structured-logging/main.py    # from examples/

Each log line is one JSON object, so you can search it ("all failed tool calls in run X")
instead of reading it. Two modes:

    prod   logs argument *names* and sizes, never values or results
    debug  also logs redacted argument values and a short, redacted preview of the result

Read alongside docs/14-observability-and-debugging/14.2-logging-tool-calls.md.
"""

from __future__ import annotations

import contextvars
import io
import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- correlation: one run ID per run

RUN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)


@contextmanager
def run_context(run_id: str | None = None) -> Iterator[str]:
    """Set the run ID for everything logged inside the `with` block (threads and asyncio tasks included)."""
    token = RUN_ID.set(run_id or uuid.uuid4().hex[:12])
    try:
        yield RUN_ID.get() or ""
    finally:
        RUN_ID.reset(token)


# --------------------------------------------------------------------------- redaction

SENSITIVE_KEYS = {"api_key", "apikey", "password", "secret", "token", "authorization", "card_number", "ssn"}
PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[REDACTED_KEY]"),  # OpenAI- and Anthropic-style keys
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer [REDACTED]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
]


def redact(value: Any) -> Any:
    """Return a copy of `value` with secrets and personal data masked. Works on nested dicts and lists."""
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for pattern, replacement in PATTERNS:
            value = pattern.sub(replacement, value)
        return value
    return value


# --------------------------------------------------------------------------- the JSON formatter

STANDARD_ATTRS = set(vars(logging.LogRecord("x", 0, "x", 0, "x", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line: time, level, event, run ID, then any `extra=` fields (redacted)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": round(record.created, 3),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "run_id": RUN_ID.get(),
        }
        entry |= {k: v for k, v in vars(record).items() if k not in STANDARD_ATTRS}
        return json.dumps(redact(entry), ensure_ascii=False, default=str)


def make_logger(stream: Any = None, name: str = "agent") -> logging.Logger:
    """A logger that writes JSON lines to `stream` (stdout by default)."""
    logger = logging.getLogger(f"{name}.{id(stream)}")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


# --------------------------------------------------------------------------- logging one tool call

Mode = Literal["prod", "debug"]


def logged_tool_call(
    logger: logging.Logger, mode: Mode, step: int, call_id: str, name: str, fn: Callable[..., str], args: dict[str, Any]
) -> tuple[str, bool]:
    """Run one tool and log a `tool.call` line about it. Returns (result, is_error)."""
    fields: dict[str, Any] = {"step": step, "tool": name, "call_id": call_id, "arg_names": sorted(args)}
    if mode == "debug":
        fields["arguments"] = args  # redacted by the formatter
    start = time.perf_counter()
    try:
        result, ok = fn(**args), True
    except Exception as exc:
        result, ok = f"Error: {type(exc).__name__}: {exc}", False
        fields["error_type"] = type(exc).__name__
    fields |= {"ok": ok, "duration_ms": round((time.perf_counter() - start) * 1000, 1), "result_chars": len(result)}
    if mode == "debug":
        fields["result_preview"] = redact(result)[:80]  # redact first, then cut: a cut can split a secret
    logger.log(logging.INFO if ok else logging.WARNING, "tool.call", extra=fields)
    return result, not ok


# --------------------------------------------------------------------------- a small agent that logs

CUSTOMERS = {"ana@example.com": {"name": "Ana", "plan": "pro", "card_number": "4242 4242 4242 4242"}}


def find_customer(email: str) -> str:
    """Look up a customer by email (fake data). The record includes a card number, as real records often do."""
    return json.dumps({"email": email, **CUSTOMERS[email]})


def open_ticket(summary: str, priority: str = "normal") -> str:
    """Open a support ticket (fake)."""
    return json.dumps({"ticket_id": "T-1042", "priority": priority})


TOOLS: dict[str, tuple[Callable[..., str], ToolSpec]] = {
    "find_customer": (
        find_customer,
        {
            "name": "find_customer",
            "description": "Find a customer record by email address.",
            "input_schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]},
        },
    ),
    "open_ticket": (
        open_ticket,
        {
            "name": "open_ticket",
            "description": "Open a support ticket. priority is 'normal' or 'high'.",
            "input_schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}, "priority": {"type": "string"}},
                "required": ["summary"],
            },
        },
    ),
}

GOAL = "I'm ana@example.com and I was charged twice this month. Please sort it out."
SCRIPT = [
    MockLLM.tool_call("find_customer", {"email": "ana@example.com"}),
    MockLLM.tool_call("open_ticket", {"summary": "Double charge for ana@example.com", "priority": "high"}),
    "Thanks Ana. I've opened ticket T-1042 with high priority; billing will refund the duplicate charge.",
]


@dataclass
class LoggingAgent:
    llm: LLM
    logger: logging.Logger
    mode: Mode = "prod"
    tools: dict[str, tuple[Callable[..., str], ToolSpec]] = field(default_factory=lambda: dict(TOOLS))
    max_steps: int = 6

    def run(self, goal: str, run_id: str | None = None) -> str:
        with run_context(run_id):
            self.logger.info("run.start", extra={"goal_chars": len(goal)})
            messages: list[Message] = [user(goal)]
            specs = [spec for _, spec in self.tools.values()]
            for step in range(1, self.max_steps + 1):
                reply = self.llm.chat(messages, system="You are a billing support agent.", tools=specs)
                self.logger.info(
                    "model.call",
                    extra={
                        "step": step,
                        "model": self.llm.model,
                        "stop_reason": reply.stop_reason,
                        "input_tokens": reply.usage.input_tokens,
                        "output_tokens": reply.usage.output_tokens,
                        "tool_calls": [c.name for c in reply.tool_calls],
                    },
                )
                messages.append(reply.to_message())
                if not reply.tool_calls:
                    self.logger.info("run.end", extra={"outcome": "answered", "steps": step})
                    return reply.text
                for call in reply.tool_calls:
                    fn = self.tools[call.name][0]
                    result, is_error = logged_tool_call(self.logger, self.mode, step, call.id, call.name, fn, call.arguments)
                    messages.append(tool_result(call.id, result, is_error=is_error))
            self.logger.warning("run.end", extra={"outcome": "step_limit", "steps": self.max_steps})
            return "I could not finish within the step limit."


def main() -> None:
    for mode in ("prod", "debug"):
        buffer = io.StringIO()
        agent = LoggingAgent(llm=get_llm(mock_responses=SCRIPT), logger=make_logger(buffer), mode=mode)  # type: ignore[arg-type]
        answer = agent.run(GOAL, run_id="run-5b1e09")
        print(f"--- {mode} logs ---")
        for line in buffer.getvalue().splitlines():
            entry = json.loads(line)
            entry.pop("ts")  # timestamps vary run to run; drop them for a readable demo
            entry.pop("duration_ms", None)
            print(json.dumps(entry, ensure_ascii=False))
        print()
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
