"""A customer support agent: route the message, answer with tools, hand off to a human when needed.

    message ─▶ hard rules ──(asks for a human, legal threat)──────────────▶ human queue
                  │
                  ▼
              router (LLM, JSON) ─▶ intent ─▶ agent loop with that intent's tools
                                                 │   lookup_order, issue_refund (policy in code)
                                                 └─▶ handoff_to_human(reason, summary) ─▶ human queue

The model decides most things, but three decisions live in code, where they
cannot be talked out of: the escalation rules, the refund limit and the step
limit. Every handoff carries a summary, so the human never has to ask the
customer to repeat themselves.

    python main.py                            # from this folder
    python 17-support-agent-triage/main.py    # from examples/

Read alongside docs/17-case-studies/17.2-customer-support-agent.md.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

AUTO_REFUND_LIMIT_EUR = 50  # above this, a person must approve
MAX_STEPS = 6

# --------------------------------------------------------------------------- fake shop backend

ORDERS = {
    "A-100": {"item": "Desk lamp", "total_eur": 39, "status": "delivered", "delivered": "2026-11-08"},
    "A-200": {"item": "Office chair", "total_eur": 189, "status": "delivered", "delivered": "2026-11-10"},
    "A-300": {"item": "Monitor arm", "total_eur": 59, "status": "shipped", "eta": "2026-11-15"},
}


@dataclass
class Desk:
    """Where side effects land: refunds issued and tickets for the human team."""

    refunds: list[dict] = field(default_factory=list)
    tickets: list[dict] = field(default_factory=list)

    def lookup_order(self, order_id: str) -> tuple[bool, str]:
        order = ORDERS.get(order_id.strip().upper())
        return (True, json.dumps({"order_id": order_id, **order})) if order else (False, f"No order {order_id!r}.")

    def issue_refund(self, order_id: str, amount_eur: float, reason: str) -> tuple[bool, str]:
        """The refund policy is enforced here, in code, whatever the model asks for."""
        order = ORDERS.get(order_id.strip().upper())
        if not order:
            return False, f"No order {order_id!r}."
        if amount_eur <= 0 or amount_eur > order["total_eur"]:
            return False, f"Invalid amount: must be between 0 and the order total ({order['total_eur']} EUR)."
        if amount_eur > AUTO_REFUND_LIMIT_EUR:
            return False, (
                f"Refunds above {AUTO_REFUND_LIMIT_EUR} EUR need a person. "
                "Call handoff_to_human with a summary. Do not promise the refund."
            )
        self.refunds.append({"order_id": order_id, "amount_eur": amount_eur, "reason": reason})
        return True, json.dumps({"refund_id": f"RF-{len(self.refunds):03d}", "amount_eur": amount_eur})

    def handoff_to_human(self, reason: str, summary: str) -> tuple[bool, str]:
        ticket = {"ticket_id": f"T-{len(self.tickets) + 1:03d}", "reason": reason, "summary": summary}
        self.tickets.append(ticket)
        return True, json.dumps(ticket)


def spec(name: str, description: str, props: dict[str, dict]) -> ToolSpec:
    return {"name": name, "description": description, "input_schema": {"type": "object", "properties": props, "required": list(props)}}


SPECS: dict[str, ToolSpec] = {
    "lookup_order": spec("lookup_order", "Look up an order by id, e.g. 'A-100'. Returns item, total, status and dates.", {"order_id": {"type": "string"}}),
    "issue_refund": spec(
        "issue_refund",
        f"Refund part or all of an order. Refunds above {AUTO_REFUND_LIMIT_EUR} EUR are refused: hand off instead.",
        {"order_id": {"type": "string"}, "amount_eur": {"type": "number"}, "reason": {"type": "string"}},
    ),
    "handoff_to_human": spec(
        "handoff_to_human",
        "Pass the conversation to a human agent. Use when policy requires it, the customer asks, or you are stuck.",
        {
            "reason": {"type": "string", "description": "Why a human is needed, in a few words."},
            "summary": {"type": "string", "description": "Customer, order, what they want, what you already checked."},
        },
    ),
}
TOOLS_BY_INTENT = {
    "order_status": ["lookup_order", "handoff_to_human"],
    "refund": ["lookup_order", "issue_refund", "handoff_to_human"],
    "other": ["handoff_to_human"],
}

# --------------------------------------------------------------------------- step 1: hard rules (no model)

ESCALATE_PATTERNS = {
    "asked for a human": r"\b(human|real person|manager|speak to someone)\b",
    "legal or chargeback": r"\b(lawyer|legal action|sue|chargeback)\b",
}


def hard_rule(message: str) -> str | None:
    """Return a reason to escalate immediately, or None. Cheap, predictable and testable."""
    for reason, pattern in ESCALATE_PATTERNS.items():
        if re.search(pattern, message, re.IGNORECASE):
            return reason
    return None


# --------------------------------------------------------------------------- step 2: router (one model call, JSON out)

ROUTER_PROMPT = (
    'Classify the customer message. Reply with JSON only: {"intent": "order_status" | "refund" | "other", '
    '"confidence": number between 0 and 1}.'
)


def route(llm: LLM, message: str) -> tuple[str, float]:
    """Ask the model for an intent; fall back to 'other' if the reply is not valid."""
    reply = llm.chat([user(message)], system=ROUTER_PROMPT, max_tokens=100)
    try:
        data = json.loads(reply.text)
        intent, confidence = data["intent"], float(data["confidence"])
    except (ValueError, KeyError, TypeError):
        return "other", 0.0
    return (intent, confidence) if intent in TOOLS_BY_INTENT else ("other", 0.0)


# --------------------------------------------------------------------------- step 3: the agent loop

AGENT_PROMPT = (
    "You are a support agent for an online shop. Be brief and friendly. Use tools to check facts; "
    "never guess order details. Only promise what a tool confirmed. "
    "If you cannot help, call handoff_to_human with a summary the human can act on without asking again."
)


@dataclass
class Outcome:
    resolved_by: str  # "agent" or "human"
    reply: str
    intent: str
    trace: list[str]


def handle(llm: LLM, desk: Desk, message: str) -> Outcome:
    trace: list[str] = []

    reason = hard_rule(message)
    if reason:  # never reaches the model
        ticket = json.loads(desk.handoff_to_human(reason, f"Customer wrote: {message}")[1])
        trace.append(f"hard rule: {reason} -> ticket {ticket['ticket_id']}")
        return Outcome("human", f"I'm passing you to a colleague now (ticket {ticket['ticket_id']}).", "escalated", trace)

    intent, confidence = route(llm, message)
    trace.append(f"router: intent={intent} confidence={confidence}")
    if confidence < 0.6:
        intent = "other"  # unsure: give the agent the safest tool set
    tools: dict[str, Callable[..., tuple[bool, str]]] = {n: getattr(desk, n) for n in TOOLS_BY_INTENT[intent]}
    specs = [SPECS[n] for n in tools]

    messages: list[Message] = [user(message)]
    failures = 0
    for _ in range(MAX_STEPS):
        reply = llm.chat(messages, system=AGENT_PROMPT, tools=specs)
        messages.append(reply.to_message())
        if not reply.tool_calls:
            trace.append("agent: answered")
            return Outcome("agent", reply.text, intent, trace)
        for call in reply.tool_calls:
            fn = tools.get(call.name)
            ok, result = fn(**call.arguments) if fn else (False, f"Tool {call.name!r} is not available here.")
            args = json.dumps(call.arguments)
            trace.append(f"tool: {call.name}({args if len(args) < 60 else args[:57] + '...'}) -> {'ok' if ok else 'refused'}")
            messages.append(tool_result(call.id, result, is_error=not ok))
            failures += not ok
            if call.name == "handoff_to_human" and ok:
                ticket = json.loads(result)
                return Outcome("human", f"I've passed this to a colleague (ticket {ticket['ticket_id']}). "
                               "They can see everything we discussed.", intent, trace)
        if failures >= 3:
            break  # stuck: stop burning tokens

    ticket = json.loads(desk.handoff_to_human("agent stuck", f"Customer wrote: {message}. Trace: {trace}")[1])
    trace.append(f"loop guard -> ticket {ticket['ticket_id']}")
    return Outcome("human", f"I've passed this to a colleague (ticket {ticket['ticket_id']}).", intent, trace)


# --------------------------------------------------------------------------- three conversations

CASES: list[tuple[str, list]] = [
    (
        "Where is my monitor arm? Order A-300.",
        [
            '{"intent": "order_status", "confidence": 0.95}',
            MockLLM.tool_call("lookup_order", {"order_id": "A-300"}),
            "Your monitor arm (order A-300) has shipped and should arrive on 15 November.",
        ],
    ),
    (
        "The chair from order A-200 arrived broken. I want my money back.",
        [
            '{"intent": "refund", "confidence": 0.9}',
            MockLLM.tool_call("lookup_order", {"order_id": "A-200"}),
            MockLLM.tool_call("issue_refund", {"order_id": "A-200", "amount_eur": 189, "reason": "Arrived broken"}),
            MockLLM.tool_call(
                "handoff_to_human",
                {
                    "reason": "Refund above auto limit",
                    "summary": "Order A-200, office chair, 189 EUR, delivered 2026-11-10, arrived broken. "
                    "Customer wants a full refund. Order checked; refund refused by policy (limit 50 EUR).",
                },
            ),
        ],
    ),
    ("This is useless. Let me speak to a real person.", []),
]


def main() -> None:
    desk = Desk()
    for message, script in CASES:
        outcome = handle(get_llm(mock_responses=script), desk, message)
        print(f"Customer: {message}")
        for line in outcome.trace:
            print(f"  {line}")
        print(f"  -> resolved by {outcome.resolved_by}: {outcome.reply}\n")
    print("Human queue:")
    for t in desk.tickets:
        print(f"  {t['ticket_id']} [{t['reason']}] {t['summary']}")


if __name__ == "__main__":
    main()
