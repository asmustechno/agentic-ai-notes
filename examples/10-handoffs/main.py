"""Handoffs: a triage agent passes control of the conversation to a specialist.

    user ─▶ triage ──transfer_to_billing──▶ billing ──list_charges, open_refund_request──▶ answer
                   └─transfer_to_tech─────▶ tech    ──check_service_status──────────────▶ answer

Unlike a supervisor (see 10-supervisor), triage does not get control back.
After a handoff the specialist becomes the active agent: it reads the same
conversation, uses its own instructions and tools, and answers the user
directly. Each handoff is shown to the model as an ordinary tool named
`transfer_to_<agent>`, the same idea the OpenAI Agents SDK uses.

    python main.py               # from this folder
    python 10-handoffs/main.py   # from examples/

Read alongside docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

Tool = tuple[Callable[..., str], ToolSpec]
HistoryFilter = Callable[[list[Message]], list[Message]]

# --------------------------------------------------------------------------- fake backends

CHARGES = {
    "C-1042": [
        {"invoice_id": "INV-881", "date": "2026-11-01", "amount_eur": 20, "plan": "Pro"},
        {"invoice_id": "INV-882", "date": "2026-11-01", "amount_eur": 20, "plan": "Pro"},
        {"invoice_id": "INV-790", "date": "2026-10-01", "amount_eur": 20, "plan": "Pro"},
    ]
}
REFUNDS: list[dict] = []
STATUS = {"sync": "degraded: delays of up to 30 minutes since 09:10 UTC", "login": "operational"}


def list_charges(customer_id: str) -> str:
    """All charges for a customer, newest first."""
    return json.dumps(CHARGES.get(customer_id, []))


def open_refund_request(invoice_id: str, reason: str) -> str:
    """Record a refund request for one invoice. Finance approves it later."""
    REFUNDS.append({"invoice_id": invoice_id, "reason": reason})
    return json.dumps({"refund_request": f"RR-{len(REFUNDS):03d}", "invoice_id": invoice_id, "eta_days": "5-7"})


def check_service_status(service: str) -> str:
    """Current status of one service."""
    return STATUS.get(service, f"Unknown service {service!r}. Known: {', '.join(STATUS)}")


def spec(name: str, description: str, **props: str) -> ToolSpec:
    """Build a tool spec whose arguments are all required strings."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props),
        },
    }


# --------------------------------------------------------------------------- agents and handoffs


@dataclass
class Handoff:
    """Permission for one agent to pass the conversation to another."""

    target: str  # name of the receiving agent
    description: str  # tells the model when to use it
    input_filter: HistoryFilter | None = None  # None = the receiver sees the full conversation

    @property
    def tool_name(self) -> str:
        return f"transfer_to_{self.target}"

    def tool_spec(self) -> ToolSpec:
        return spec(self.tool_name, self.description, reason="One line: why this agent should take over.")


@dataclass
class Agent:
    name: str
    llm: LLM
    instructions: str
    tools: dict[str, Tool] = field(default_factory=dict)
    handoffs: list[Handoff] = field(default_factory=list)


@dataclass
class Runner:
    """Runs whichever agent is active, and switches agent when the model calls a transfer tool."""

    agents: dict[str, Agent]
    max_turns: int = 10  # model calls in total, across all agents
    max_handoffs: int = 3  # stops agents bouncing the user back and forth forever
    trace: list[str] = field(default_factory=list)

    def run(self, messages: list[Message], start: str) -> tuple[str, str]:
        """Return (final answer, name of the agent that gave it)."""
        active = self.agents[start]
        handoffs_done = 0
        for _ in range(self.max_turns):
            transfers = {h.tool_name: h for h in active.handoffs}
            specs = [s for _, s in active.tools.values()] + [h.tool_spec() for h in active.handoffs]
            reply = active.llm.chat(messages, system=active.instructions, tools=specs or None)
            messages.append(reply.to_message())
            if not reply.tool_calls:
                self.trace.append(f"[{active.name}] answer: {reply.text}")
                return reply.text, active.name

            chosen: Handoff | None = None
            for call in reply.tool_calls:
                if call.name in transfers:
                    if chosen is not None:  # only one handoff per turn
                        messages.append(tool_result(call.id, "Ignored: one transfer per turn.", is_error=True))
                    elif handoffs_done >= self.max_handoffs:
                        messages.append(tool_result(call.id, "Transfer limit reached. Answer the user yourself.", is_error=True))
                    else:
                        chosen = transfers[call.name]
                        messages.append(tool_result(call.id, f"Transferred to {chosen.target}."))
                        self.trace.append(f"[{active.name}] handoff -> {chosen.target} (reason: {call.arguments.get('reason', '')})")
                elif call.name in active.tools:
                    fn, _ = active.tools[call.name]
                    result = fn(**call.arguments)
                    self.trace.append(f"[{active.name}] {call.name}({call.arguments}) -> {_clip(result)}")
                    messages.append(tool_result(call.id, result))
                else:
                    messages.append(tool_result(call.id, f"Unknown tool {call.name!r}", is_error=True))

            if chosen is not None:  # control passes; the next loop iteration runs the new agent
                handoffs_done += 1
                active = self.agents[chosen.target]
                if chosen.input_filter:
                    messages[:] = chosen.input_filter(messages)
        return "Sorry, I could not finish. A human colleague will follow up.", active.name


def _clip(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def last_user_message_only(messages: list[Message]) -> list[Message]:
    """A history filter: the receiver sees only what the user last said, not the triage chatter."""
    last = next(m for m in reversed(messages) if m["role"] == "user")
    return [user(last["content"])]


# --------------------------------------------------------------------------- the team

TRIAGE_PROMPT = (
    "You are the front desk for a software company. Do not solve problems yourself. "
    "Decide who should help and transfer: billing for charges, invoices and refunds; tech for outages, "
    "errors and bugs. If the request is unclear, ask one short question."
)
BILLING_PROMPT = (
    "You are the billing specialist. Use list_charges to check the facts before you answer. "
    "If a charge is clearly a duplicate, open a refund request for the newer invoice. "
    "If the problem is technical, transfer to tech."
)
TECH_PROMPT = (
    "You are the technical support specialist. Use check_service_status before blaming the user. "
    "If the problem is about money, transfer to billing."
)

QUESTION = "Hi, I was charged twice for my Pro plan this month. My customer id is C-1042."

SCRIPTS: dict[str, list] = {
    "triage": [MockLLM.tool_call("transfer_to_billing", {"reason": "Possible duplicate charge on the Pro plan."})],
    "billing": [
        MockLLM.tool_call("list_charges", {"customer_id": "C-1042"}),
        MockLLM.tool_call("open_refund_request", {"invoice_id": "INV-882", "reason": "Duplicate charge on 2026-11-01"}),
        "You're right: you were charged 20 EUR twice on 1 November (INV-881 and INV-882). I've opened refund "
        "request RR-001 for INV-882. The money should be back in 5-7 days.",
    ],
    "tech": [],
}


def build_runner(llms: dict[str, LLM], *, filter_history: bool = False) -> Runner:
    """Three peers. Triage can reach both specialists; the specialists can reach each other."""
    REFUNDS.clear()  # a fresh fake backend for every run
    f = last_user_message_only if filter_history else None
    to_billing = Handoff("billing", "Transfer to the billing specialist (charges, invoices, refunds).", f)
    to_tech = Handoff("tech", "Transfer to the technical specialist (outages, errors, bugs).", f)
    agents = {
        "triage": Agent("triage", llms["triage"], TRIAGE_PROMPT, handoffs=[to_billing, to_tech]),
        "billing": Agent(
            "billing",
            llms["billing"],
            BILLING_PROMPT,
            {
                "list_charges": (list_charges, spec("list_charges", "List a customer's charges.", customer_id="e.g. 'C-1042'")),
                "open_refund_request": (
                    open_refund_request,
                    spec("open_refund_request", "Open a refund request for one invoice.", invoice_id="e.g. 'INV-882'", reason="Short reason"),
                ),
            },
            handoffs=[to_tech],
        ),
        "tech": Agent(
            "tech",
            llms["tech"],
            TECH_PROMPT,
            {"check_service_status": (check_service_status, spec("check_service_status", "Status of one service.", service="'sync' or 'login'"))},
            handoffs=[to_billing],
        ),
    }
    return Runner(agents)


def main() -> None:
    llms = {name: get_llm(mock_responses=script) for name, script in SCRIPTS.items()}
    runner = build_runner(llms)
    print(f"User: {QUESTION}\n")
    answer, who = runner.run([user(QUESTION)], start="triage")
    print("\n".join(runner.trace))
    print(f"\nAnswered by: {who}\nAnswer: {answer}")


if __name__ == "__main__":
    main()
