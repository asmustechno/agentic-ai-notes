"""Human-in-the-loop: approval gates, edits, rejection, escalation, and pause/resume.

A support agent can look up orders freely, but `issue_refund` above a limit needs a person:

    approve -> the tool runs as the model asked
    edit    -> the tool runs with the human's corrected arguments, and the model is told
    reject  -> the tool does not run; the model gets an error result with the reason and must adapt

Two ways to ask the human:

    1. approver callback  : the agent calls approver(request) and waits (CLI, Slack bot, tests)
    2. pause and resume   : with no callback, run() returns status="paused" and a JSON-safe state.
                            Store it anywhere (database, queue). Later, resume(state, decision).

The model can also hand the whole case to a person with the `escalate_to_human` tool.

    python main.py                         # from this folder
    python 09-human-in-the-loop/main.py    # from examples/

Read alongside docs/09-agent-design-patterns/09.6-human-in-the-loop.md.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolCall, ToolSpec, get_llm, tool_result, user  # noqa: E402

AUTO_APPROVE_LIMIT = 20.0  # refunds up to this amount need no human

# --------------------------------------------------------------------------- tools (fake data)

ORDERS = {"1234": {"item": "Blender", "price": 89.0, "shipping": 0.0, "status": "delivered"}}
REFUNDS: list[dict[str, Any]] = []  # what was actually refunded, so you can check nothing ran unapproved


def get_order(order_id: str) -> str:
    order = ORDERS.get(order_id)
    return json.dumps({"order_id": order_id, **order}) if order else f"No order {order_id}"


def issue_refund(order_id: str, amount: float, reason: str) -> str:
    REFUNDS.append({"order_id": order_id, "amount": amount, "reason": reason})
    return f"Refunded ${amount:.2f} for order {order_id} (ref R-{7780 + len(REFUNDS)})."


TOOLS: dict[str, Callable[..., str]] = {"get_order": get_order, "issue_refund": issue_refund}
SPECS: list[ToolSpec] = [
    {
        "name": "get_order",
        "description": "Look up an order by id. Returns item, price, shipping cost and status.",
        "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
    },
    {
        "name": "issue_refund",
        "description": f"Refund money to the customer. Refunds over ${AUTO_APPROVE_LIMIT:.0f} wait for human approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number", "description": "Amount in USD."},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand the case to a human agent when you cannot or should not resolve it yourself.",
        "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
    },
]
SYSTEM = (
    "You are a support agent for a home-goods shop. Look up the order before acting. "
    "Refund only what the customer paid. If a refund is rejected, or you are unsure, escalate to a human."
)


def needs_approval(call: ToolCall) -> str | None:
    """The approval policy, in code. Returns the reason approval is needed, or None."""
    if call.name == "issue_refund" and float(call.arguments.get("amount", 0)) > AUTO_APPROVE_LIMIT:
        return f"refund over ${AUTO_APPROVE_LIMIT:.0f}"
    return None


# --------------------------------------------------------------------------- human decisions


@dataclass
class ApprovalRequest:
    """What the human sees: the exact action, its arguments, and why it was stopped."""

    tool: str
    arguments: dict[str, Any]
    reason: str


@dataclass
class Decision:
    action: Literal["approve", "edit", "reject"]
    arguments: dict[str, Any] | None = None  # for "edit": the corrected arguments
    note: str = ""  # shown to the model, e.g. why it was rejected


Approver = Callable[[ApprovalRequest], Decision]


@dataclass
class RunResult:
    status: Literal["done", "paused", "escalated", "step_limit"]
    answer: str = ""
    pending: ApprovalRequest | None = None
    state: dict[str, Any] | None = None  # JSON-safe; pass to resume()
    log: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- saving and loading state


def _to_json(messages: list[Message]) -> list[dict[str, Any]]:
    out = []
    for m in messages:
        m = dict(m)
        if "tool_calls" in m:
            m["tool_calls"] = [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in m["tool_calls"]]
        if "_raw" in m:  # Anthropic content blocks are pydantic models: store them as plain dicts
            blocks = m["_raw"]["content"]
            m["_raw"] = {"provider": m["_raw"]["provider"], "content": [_block_to_dict(b) for b in blocks]}
        out.append(m)
    return out


def _block_to_dict(block: Any) -> Any:
    return block.model_dump(mode="json", exclude_none=True) if hasattr(block, "model_dump") else block


def _from_json(messages: list[dict[str, Any]]) -> list[Message]:
    out = []
    for m in messages:
        m = dict(m)
        if "tool_calls" in m:
            m["tool_calls"] = [ToolCall(**c) for c in m["tool_calls"]]
        out.append(m)
    return out


# --------------------------------------------------------------------------- the agent


@dataclass
class SupportAgent:
    llm: LLM
    max_steps: int = 8
    log: list[str] = field(default_factory=list)

    def run(self, goal: str, approver: Approver | None = None) -> RunResult:
        return self._loop([user(goal)], [], approver)

    def resume(self, state: dict[str, Any], decision: Decision, approver: Approver | None = None) -> RunResult:
        """Continue a paused run with the human's decision about the pending call."""
        messages = _from_json(state["messages"])
        pending = [ToolCall(**c) for c in state["pending_calls"]]
        first, rest = pending[0], pending[1:]
        messages.append(self._apply(first, decision))
        return self._loop(messages, rest, approver)

    # -- internals

    def _loop(self, messages: list[Message], queued: list[ToolCall], approver: Approver | None) -> RunResult:
        for _ in range(self.max_steps):
            # Run any tool calls still waiting from the last model turn.
            while queued:
                call = queued.pop(0)
                if call.name == "escalate_to_human":
                    self.log.append(f"escalated: {call.arguments.get('summary', '')}")
                    return RunResult("escalated", answer=call.arguments.get("summary", ""), log=self.log)
                reason = needs_approval(call)
                if reason is None:
                    messages.append(self._run_tool(call, call.arguments))
                    continue
                request = ApprovalRequest(call.name, dict(call.arguments), reason)
                if approver is None:  # nobody to ask right now: pause and hand back a resumable state
                    self.log.append(f"paused: {call.name}({call.arguments}) needs approval ({reason})")
                    state = {
                        "messages": _to_json(messages),
                        "pending_calls": [
                            {"id": c.id, "name": c.name, "arguments": c.arguments} for c in [call, *queued]
                        ],
                    }
                    return RunResult("paused", pending=request, state=state, log=self.log)
                messages.append(self._apply(call, approver(request)))

            reply = self.llm.chat(messages, system=SYSTEM, tools=SPECS)
            messages.append(reply.to_message())
            if not reply.tool_calls:
                return RunResult("done", answer=reply.text, log=self.log)
            queued = list(reply.tool_calls)
        return RunResult("step_limit", answer="Stopped: step limit reached.", log=self.log)

    def _run_tool(self, call: ToolCall, arguments: dict[str, Any]) -> Message:
        output = TOOLS[call.name](**arguments)
        self.log.append(f"tool: {call.name}({arguments}) -> {output}")
        return tool_result(call.id, output)

    def _apply(self, call: ToolCall, decision: Decision) -> Message:
        """Turn the human's decision into the tool result the model will read."""
        edited = f" -> {decision.arguments}" if decision.action == "edit" else ""
        self.log.append(f"human: {decision.action}{edited}" + (f" ({decision.note})" if decision.note else ""))
        if decision.action == "approve":
            return self._run_tool(call, call.arguments)
        if decision.action == "edit":
            msg = self._run_tool(call, decision.arguments or call.arguments)
            msg["content"] = (
                f"A human reviewer changed the arguments to {decision.arguments}. {decision.note} "
                f"Result: {msg['content']}"
            )
            return msg
        self.log.append(f"tool: {call.name} NOT run (rejected)")
        return tool_result(call.id, f"A human reviewer rejected this action. Reason: {decision.note}", is_error=True)


# --------------------------------------------------------------------------- an offline demo

GOAL = "Order 1234: the customer says the blender arrived broken and wants their money back."

SCRIPT_EDIT = [  # part 1: pause, human edits the amount, resume
    MockLLM.tool_call("get_order", {"order_id": "1234"}),
    MockLLM.tool_call("issue_refund", {"order_id": "1234", "amount": 99.0, "reason": "arrived broken"}),
    "I've refunded $89.00 for the broken blender on order 1234 (ref R-7781). "
    "The customer should see it in 3-5 working days.",
]
SCRIPT_REJECT = [  # part 2: approver callback rejects, the model escalates
    MockLLM.tool_call("get_order", {"order_id": "1234"}),
    MockLLM.tool_call("issue_refund", {"order_id": "1234", "amount": 89.0, "reason": "arrived broken"}),
    MockLLM.tool_call("escalate_to_human", {"summary": "Refund for broken blender (order 1234) was rejected "
                                                       "pending photos. Please contact the customer."}),
]


def main() -> None:
    print(f"Goal: {GOAL}\n")

    print("PART 1: pause, save state, a human edits the refund, resume")
    agent = SupportAgent(get_llm(mock_responses=SCRIPT_EDIT))
    result = agent.run(GOAL)  # no approver: the run pauses at the risky call
    saved = json.dumps(result.state)  # e.g. store in a database while the human decides
    print(f"  status: {result.status}; waiting on {result.pending.tool}({result.pending.arguments})")
    print(f"  saved state: {len(saved)} bytes of JSON")
    decision = Decision("edit", {"order_id": "1234", "amount": 89.0, "reason": "arrived broken"},
                        note="Shipping was free, so refund the item price only.")
    result = SupportAgent(agent.llm).resume(json.loads(saved), decision)  # a fresh agent object, as after a restart
    print("  " + "\n  ".join(agent.log + result.log))
    print(f"  status: {result.status}\n  answer: {result.answer}\n")

    print("PART 2: an approval callback rejects the refund, the agent escalates")

    def approver(request: ApprovalRequest) -> Decision:  # in a real app: a CLI prompt, a Slack button, a web form
        return Decision("reject", note="Ask the customer for photos of the damage first.")

    agent = SupportAgent(get_llm(mock_responses=SCRIPT_REJECT))
    result = agent.run(GOAL, approver=approver)
    print("  " + "\n  ".join(result.log))
    print(f"  status: {result.status}")
    print(f"\nRefunds actually issued: {REFUNDS}")


if __name__ == "__main__":
    main()
