"""Debug a broken agent step by step: reproduce, read the trace, locate the part, fix, add a regression test.

    python main.py                              # from this folder
    python 14-debugging-walkthrough/main.py     # from examples/

The bug report: "I asked where my order is. The bot said 'Let me look that up for you.' and stopped."

1. Reproduce: replay the model replies recorded from the failing run (recorded_run.json) with MockLLM,
   so the bug happens the same way every time, offline, for free.
2. Read the trace: every model call and tool call, with stop reasons.
3. Locate the part (model, instructions, tools, memory or loop) that went wrong.
4. Fix it.
5. Keep the recording as a regression test (see tests/test_main.py).

Read alongside docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolCall, ToolSpec, Usage, tool_result, user  # noqa: E402

HERE = Path(__file__).resolve().parent
RECORDING = HERE / "recorded_run.json"

# --------------------------------------------------------------------------- recording and replaying model replies


def response_to_dict(r: LLMResponse) -> dict[str, Any]:
    """The parts of a reply worth keeping in a recording (no raw provider object)."""
    return {
        "text": r.text,
        "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in r.tool_calls],
        "stop_reason": r.stop_reason,
        "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
    }


def response_from_dict(d: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        text=d["text"],
        tool_calls=[ToolCall(id=c["id"], name=c["name"], arguments=c["arguments"]) for c in d["tool_calls"]],
        stop_reason=d["stop_reason"],
        usage=Usage(**d["usage"]),
    )


class RecordingLLM(LLM):
    """Wrap any model and keep a copy of every reply, so a failing run can be saved and replayed."""

    def __init__(self, inner: LLM) -> None:
        self.inner, self.provider, self.model = inner, inner.provider, inner.model
        self.replies: list[dict[str, Any]] = []

    def chat(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        reply = self.inner.chat(messages, **kwargs)
        self.replies.append(response_to_dict(reply))
        return reply

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"model": self.model, "replies": self.replies}, indent=2), encoding="utf-8")


def load_recording(path: Path = RECORDING) -> list[LLMResponse]:
    """Turn a recording back into a MockLLM script."""
    return [response_from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))["replies"]]


# --------------------------------------------------------------------------- a tiny trace recorder


@dataclass
class Trace:
    """A flat list of events. Enough to debug with; chapter 14.3 shows the OpenTelemetry version."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, kind: str, **data: Any) -> None:
        self.events.append({"kind": kind, **data})

    def render(self) -> str:
        lines = []
        for e in self.events:
            if e["kind"] == "model":
                calls = ", ".join(f"{c}" for c in e["tool_calls"]) or "-"
                text = e["text"] if len(e["text"]) <= 40 else e["text"][:37] + "..."
                lines.append(f"step {e['step']}  model  stop={e['stop_reason']:<9} tools=[{calls}]  text={text!r}")
            elif e["kind"] == "tool":
                status = "ERROR" if e["is_error"] else "ok"
                lines.append(f"step {e['step']}  tool   {e['name']}({e['arguments']}) -> {status}, {len(e['result'])} chars")
            else:
                lines.append(f"        end    {e['reason']}")
        return "\n".join(lines)


def find_problems(trace: Trace) -> list[str]:
    """Automatic checks a human would otherwise do by eye when reading a trace."""
    problems: list[str] = []
    events = trace.events
    for i, e in enumerate(events):
        if e["kind"] != "model":
            continue
        following = events[i + 1] if i + 1 < len(events) else None
        if e["tool_calls"] and (following is None or following["kind"] != "tool"):
            problems.append(f"step {e['step']}: model asked for {e['tool_calls']} but no tool ran (loop stopped early?)")
        if e["stop_reason"] in ("max_tokens", "refusal"):
            problems.append(f"step {e['step']}: stop_reason={e['stop_reason']} (answer may be cut off or refused)")
    calls = [(e["name"], json.dumps(e["arguments"], sort_keys=True)) for e in events if e["kind"] == "tool"]
    for call in set(calls):
        if calls.count(call) >= 3:
            problems.append(f"tool {call[0]} called {calls.count(call)} times with the same arguments (stuck in a loop?)")
    return problems


# --------------------------------------------------------------------------- the agent (broken and fixed)

ORDERS = {"1234": {"status": "shipped", "carrier": "ParcelCo", "tracking_id": "PC-998877"}}
ETAS = {"PC-998877": "2026-11-16"}


def get_order(order_id: str) -> str:
    return json.dumps(ORDERS[order_id]) if order_id in ORDERS else f"Error: no order {order_id!r}"


def get_shipping_eta(tracking_id: str) -> str:
    return json.dumps({"eta": ETAS[tracking_id]}) if tracking_id in ETAS else f"Error: unknown tracking ID {tracking_id!r}"


def spec(name: str, description: str, param: str) -> ToolSpec:
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": {param: {"type": "string"}}, "required": [param]},
    }


TOOLS: dict[str, tuple[Callable[..., str], ToolSpec]] = {
    "get_order": (get_order, spec("get_order", "Get status, carrier and tracking ID for an order.", "order_id")),
    "get_shipping_eta": (get_shipping_eta, spec("get_shipping_eta", "Get the delivery date for a tracking ID.", "tracking_id")),
}
INSTRUCTIONS = "You are an order-support agent. Look things up with the tools; never guess."
GOAL = "Where is my order 1234 and when will it arrive?"


@dataclass
class Agent:
    """The fixed agent: the loop ends only when the model asks for no more tools."""

    llm: LLM
    trace: Trace = field(default_factory=Trace)
    max_steps: int = 6

    def is_final(self, reply: LLMResponse) -> bool:
        return not reply.tool_calls  # ⑤ LOOP: "no tool calls" is the signal that the model is done

    def run(self, goal: str) -> str:
        messages: list[Message] = [user(goal)]
        specs = [s for _, s in TOOLS.values()]
        for step in range(1, self.max_steps + 1):
            reply = self.llm.chat(messages, system=INSTRUCTIONS, tools=specs)
            self.trace.add(
                "model", step=step, stop_reason=reply.stop_reason, text=reply.text,
                tool_calls=[c.name for c in reply.tool_calls],
            )
            messages.append(reply.to_message())
            if self.is_final(reply):
                self.trace.add("end", reason=f"model finished at step {step}")
                return reply.text
            for call in reply.tool_calls:
                result = TOOLS[call.name][0](**call.arguments)
                is_error = result.startswith("Error")
                self.trace.add("tool", step=step, name=call.name, arguments=call.arguments, result=result, is_error=is_error)
                messages.append(tool_result(call.id, result, is_error=is_error))
        self.trace.add("end", reason="step limit")
        return "I could not finish within the step limit."


class BrokenAgent(Agent):
    """The bug from the report, as it was in the code."""

    def is_final(self, reply: LLMResponse) -> bool:
        return bool(reply.text)  # BUG: any text counts as the final answer, even "Let me look that up."


def main() -> None:
    print("1) Reproduce with the recorded replies\n")
    broken = BrokenAgent(llm=MockLLM(load_recording()))
    answer = broken.run(GOAL)
    print(broken.trace.render())
    print(f"\n   Answer: {answer}\n")

    print("2) Read the trace: automatic checks\n")
    for problem in find_problems(broken.trace) or ["(none)"]:
        print(f"   - {problem}")

    print("\n3) Locate: model asked for a tool (stop=tool_use) and the loop returned anyway -> part 5, the loop.")
    print("   is_final() treats any text as the final answer. Fix: finish only when there are no tool calls.\n")

    print("4) Re-run the same recording with the fix\n")
    fixed = Agent(llm=MockLLM(load_recording()))
    answer = fixed.run(GOAL)
    print(fixed.trace.render())
    print(f"\n   Answer: {answer}")
    print(f"   Problems found: {find_problems(fixed.trace) or 'none'}")


if __name__ == "__main__":
    main()
