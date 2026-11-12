"""Human approval for risky actions: risk tiers, a dry-run preview, and an audit log.

A billing agent can read invoices, add notes and issue refunds. Every tool has a
risk tier. Reads run at once. Writes run and are logged. Irreversible actions stop
and show a person a preview (made by a dry run) of exactly what will happen. The
person approves or denies, and every decision goes in an append-only JSONL log.

    python main.py                         # from this folder
    python 13-approval-gate/main.py        # from examples/

Read alongside docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402


class Risk(str, Enum):
    READ = "read"  # no side effects: run immediately
    WRITE = "write"  # reversible side effects: run and log
    IRREVERSIBLE = "irreversible"  # money moves, data is deleted, messages leave: ask a human first


# --------------------------------------------------------------------------- the (fake) billing system

INVOICES = {
    "INV-1001": {"customer": "Ada", "amount_gbp": 40.00, "card": "4242"},
    "INV-1002": {"customer": "Ada", "amount_gbp": 950.00, "card": "4242"},
}


@dataclass
class Billing:
    notes: dict[str, list[str]] = field(default_factory=dict)
    refunds: list[dict[str, Any]] = field(default_factory=list)

    def get_invoice(self, invoice_id: str) -> str:
        inv = INVOICES.get(invoice_id)
        return json.dumps({"invoice_id": invoice_id, **inv}) if inv else f"No invoice {invoice_id}"

    def add_note(self, invoice_id: str, text: str) -> str:
        self.notes.setdefault(invoice_id, []).append(text)
        return "Note added."

    def refund(self, invoice_id: str, amount_gbp: float, dry_run: bool = False) -> str:
        inv = INVOICES.get(invoice_id)
        if inv is None:
            return f"No invoice {invoice_id}"
        if amount_gbp > inv["amount_gbp"]:
            return f"Refund £{amount_gbp:.2f} is more than the invoice total £{inv['amount_gbp']:.2f}"
        summary = f"refund £{amount_gbp:.2f} to {inv['customer']}'s card ending {inv['card']} for {invoice_id}"
        if dry_run:  # the preview: same checks, no side effects
            return f"Would {summary}."
        self.refunds.append({"invoice_id": invoice_id, "amount_gbp": amount_gbp})
        return f"Done: {summary}."


def _spec(name: str, description: str, props: dict[str, dict[str, str]]) -> ToolSpec:
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": props, "required": list(props)},
    }


STR, NUM = {"type": "string"}, {"type": "number"}
TOOLS: dict[str, tuple[Risk, ToolSpec]] = {
    "get_invoice": (Risk.READ, _spec("get_invoice", "Look up an invoice by id.", {"invoice_id": STR})),
    "add_note": (Risk.WRITE, _spec("add_note", "Add an internal note to an invoice.", {"invoice_id": STR, "text": STR})),
    "refund": (
        Risk.IRREVERSIBLE,
        _spec("refund", "Refund money to the customer's card. Needs human approval.", {"invoice_id": STR, "amount_gbp": NUM}),
    ),
}


# --------------------------------------------------------------------------- approval gate + audit log


@dataclass(frozen=True)
class ApprovalRequest:
    tool: str
    arguments: dict[str, Any]
    preview: str
    reason: str  # what the agent said it was doing

    @property
    def fingerprint(self) -> str:
        """Binds the approval to these exact arguments, so they cannot change after approval."""
        blob = json.dumps({"tool": self.tool, "arguments": self.arguments}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


@dataclass
class Decision:
    approved: bool
    approver: str
    note: str = ""


Approver = Callable[[ApprovalRequest], Decision]


def cli_approver(req: ApprovalRequest) -> Decision:
    """Ask in the terminal. Anything other than 'y' is a no: deny by default."""
    print(f"\nAPPROVAL NEEDED  {req.tool}  [{req.fingerprint}]\n  {req.preview}\n  agent says: {req.reason}")
    answer = input("  approve? [y/N] ").strip().lower()
    return Decision(approved=answer == "y", approver="cli-user")


class AuditLog:
    """Append-only JSON Lines: one event per line, never rewritten."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, event: str, **data: Any) -> None:
        row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def rows(self) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]


@dataclass
class Gate:
    billing: Billing
    approver: Approver
    audit: AuditLog

    def run(self, name: str, args: dict[str, Any], reason: str) -> tuple[str, bool]:
        """Run one tool call through the gate. Returns (result, is_error)."""
        if name not in TOOLS:
            return f"Unknown tool {name}", True
        risk = TOOLS[name][0]
        fn = getattr(self.billing, name)
        if risk is Risk.IRREVERSIBLE:
            preview = fn(**args, dry_run=True)
            if not preview.startswith("Would "):  # the dry run itself failed: no need to ask anyone
                self.audit.write("rejected", tool=name, arguments=args, result=preview)
                return preview, True
            req = ApprovalRequest(name, dict(args), preview, reason)
            decision = self.approver(req)
            self.audit.write(
                "approved" if decision.approved else "denied",
                tool=name, arguments=args, fingerprint=req.fingerprint,
                approver=decision.approver, note=decision.note,
            )
            if not decision.approved:
                return f"Denied by a human reviewer. {decision.note}".strip(), True
            args = req.arguments  # run exactly what was approved
        result = fn(**args)
        self.audit.write("executed", tool=name, risk=risk.value, arguments=args, result=result)
        return result, False


# --------------------------------------------------------------------------- the agent loop

SYSTEM = (
    "You are a billing assistant. Refunds need human approval; if one is denied, "
    "do not retry it. Add a note explaining what happened instead."
)
GOAL = "Ada wants full refunds for INV-1001 and INV-1002. Please sort it out."
SCRIPT = [
    MockLLM.tool_calls([("get_invoice", {"invoice_id": "INV-1001"}), ("get_invoice", {"invoice_id": "INV-1002"})]),
    MockLLM.tool_call("refund", {"invoice_id": "INV-1001", "amount_gbp": 40.0}, text="Refunding INV-1001 in full."),
    MockLLM.tool_call("refund", {"invoice_id": "INV-1002", "amount_gbp": 950.0}, text="Refunding INV-1002 in full."),
    MockLLM.tool_call("add_note", {"invoice_id": "INV-1002", "text": "Full refund denied by reviewer; escalated."}),
    "I refunded £40.00 for INV-1001. The £950.00 refund for INV-1002 was denied by a reviewer, "
    "so I added a note and it has been escalated.",
]


def run_agent(llm: LLM, gate: Gate, goal: str = GOAL, max_steps: int = 8) -> str:
    messages: list[Message] = [user(goal)]
    specs = [spec for _, spec in TOOLS.values()]
    for _ in range(max_steps):
        reply = llm.chat(messages, system=SYSTEM, tools=specs)
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text
        for call in reply.tool_calls:
            result, is_error = gate.run(call.name, call.arguments, reason=reply.text)
            messages.append(tool_result(call.id, result, is_error=is_error))
    return "Step limit reached."


def scripted_approver(decisions: list[Decision]) -> Approver:
    """For demos and tests: hand out pre-written decisions in order, and print each request."""
    queue = list(decisions)

    def approve(req: ApprovalRequest) -> Decision:
        decision = queue.pop(0)
        verdict = "APPROVED" if decision.approved else "DENIED"
        print(f"  [approval {req.fingerprint}] {req.preview} -> {verdict} by {decision.approver}")
        return decision

    return approve


def main() -> None:
    print(f"Goal: {GOAL}\n")
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "audit.jsonl")
        approver = scripted_approver([
            Decision(True, "sam@billing"),
            Decision(False, "sam@billing", note="Over £500: needs a manager."),
        ])
        billing = Billing()
        answer = run_agent(get_llm(mock_responses=SCRIPT), Gate(billing, approver, audit))
        print(f"\nAnswer: {answer}\n\nAudit log:")
        for row in audit.rows():
            extra = f"by {row['approver']}" if "approver" in row else f"risk={row.get('risk', '-')}"
            print(f"  {row['event']:<9} {row['tool']:<11} {json.dumps(row['arguments'])}  {extra}")
        print(f"\nRefunds actually made: {billing.refunds}")


if __name__ == "__main__":
    main()
