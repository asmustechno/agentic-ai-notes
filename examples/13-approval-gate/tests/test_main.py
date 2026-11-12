"""Risk tiers, previews, denials and the audit log behave as promised. Offline."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def make_gate(tmp_path, decisions):
    billing = main.Billing()
    audit = main.AuditLog(tmp_path / "audit.jsonl")
    seen: list = []

    def approver(req):
        seen.append(req)
        return decisions.pop(0)

    return main.Gate(billing, approver, audit), billing, audit, seen


def test_full_run_refunds_only_what_was_approved(tmp_path) -> None:
    gate, billing, audit, seen = make_gate(
        tmp_path, [main.Decision(True, "sam"), main.Decision(False, "sam", "too big")]
    )
    llm = MockLLM(main.SCRIPT)
    answer = main.run_agent(llm, gate)
    assert billing.refunds == [{"invoice_id": "INV-1001", "amount_gbp": 40.0}]
    assert "denied" in answer
    assert [r.tool for r in seen] == ["refund", "refund"]  # reads and notes never asked anyone
    events = [(r["event"], r["tool"]) for r in audit.rows()]
    assert ("denied", "refund") in events and ("approved", "refund") in events
    # The model was told about the denial as an error, with the reviewer's note.
    denial = [m for m in llm.calls[3]["messages"] if m["role"] == "tool"][-1]
    assert denial["is_error"] and "too big" in denial["content"]


def test_preview_is_a_dry_run_with_no_side_effects(tmp_path) -> None:
    gate, billing, _, seen = make_gate(tmp_path, [main.Decision(False, "sam")])
    gate.run("refund", {"invoice_id": "INV-1001", "amount_gbp": 40.0}, reason="")
    assert seen[0].preview == "Would refund £40.00 to Ada's card ending 4242 for INV-1001."
    assert billing.refunds == []


def test_invalid_refund_is_rejected_without_asking_a_human(tmp_path) -> None:
    gate, billing, audit, seen = make_gate(tmp_path, [])
    result, is_error = gate.run("refund", {"invoice_id": "INV-1001", "amount_gbp": 999.0}, reason="")
    assert is_error and "more than the invoice total" in result
    assert seen == [] and billing.refunds == []
    assert audit.rows()[0]["event"] == "rejected"


def test_write_tier_runs_without_approval_but_is_logged(tmp_path) -> None:
    gate, billing, audit, seen = make_gate(tmp_path, [])
    gate.run("add_note", {"invoice_id": "INV-1001", "text": "hi"}, reason="")
    assert billing.notes == {"INV-1001": ["hi"]} and seen == []
    assert audit.rows()[0] | {"ts": None} == {
        "ts": None, "event": "executed", "tool": "add_note", "risk": "write",
        "arguments": {"invoice_id": "INV-1001", "text": "hi"}, "result": "Note added.",
    }


def test_fingerprint_binds_approval_to_exact_arguments() -> None:
    a = main.ApprovalRequest("refund", {"invoice_id": "INV-1001", "amount_gbp": 40.0}, "p", "r")
    b = main.ApprovalRequest("refund", {"invoice_id": "INV-1001", "amount_gbp": 400.0}, "p", "r")
    assert a.fingerprint != b.fingerprint


def test_cli_approver_denies_by_default(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    req = main.ApprovalRequest("refund", {}, "Would refund", "")
    assert main.cli_approver(req).approved is False
