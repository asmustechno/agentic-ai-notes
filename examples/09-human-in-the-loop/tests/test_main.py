"""Human-in-the-loop: nothing risky runs without a decision. Offline, with MockLLM."""

import json

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


@pytest.fixture(autouse=True)
def clear_refunds():
    main.REFUNDS.clear()
    yield
    main.REFUNDS.clear()


def refund_call(amount: float):
    return MockLLM.tool_call("issue_refund", {"order_id": "1234", "amount": amount, "reason": "broken"})


def test_risky_call_pauses_and_runs_nothing() -> None:
    llm = MockLLM(main.SCRIPT_EDIT)
    result = main.SupportAgent(llm).run(main.GOAL)
    assert result.status == "paused"
    assert result.pending.tool == "issue_refund" and result.pending.arguments["amount"] == 99.0
    assert main.REFUNDS == []
    json.dumps(result.state)  # the state is JSON-safe, so it can be stored anywhere


def test_resume_with_edit_runs_the_edited_arguments_and_tells_the_model() -> None:
    llm = MockLLM(main.SCRIPT_EDIT)
    paused = main.SupportAgent(llm).run(main.GOAL)
    state = json.loads(json.dumps(paused.state))  # round-trip, as if loaded from a database
    decision = main.Decision("edit", {"order_id": "1234", "amount": 89.0, "reason": "broken"}, note="Free shipping.")
    result = main.SupportAgent(llm).resume(state, decision)
    assert result.status == "done" and "$89.00" in result.answer
    assert main.REFUNDS == [{"order_id": "1234", "amount": 89.0, "reason": "broken"}]
    last_tool_msg = llm.calls[-1]["messages"][-1]
    assert last_tool_msg["role"] == "tool" and "human reviewer changed the arguments" in last_tool_msg["content"]


def test_approve_runs_the_original_arguments() -> None:
    llm = MockLLM([refund_call(50.0), "Done."])
    result = main.SupportAgent(llm).run("refund", approver=lambda req: main.Decision("approve"))
    assert result.status == "done" and main.REFUNDS[0]["amount"] == 50.0


def test_reject_sends_an_error_result_and_the_model_can_escalate() -> None:
    llm = MockLLM(main.SCRIPT_REJECT)
    seen = []

    def approver(request):
        seen.append(request)
        return main.Decision("reject", note="Need photos.")

    result = main.SupportAgent(llm).run(main.GOAL, approver=approver)
    assert result.status == "escalated" and "order 1234" in result.answer
    assert main.REFUNDS == []
    assert seen[0].reason == "refund over $20"
    rejected = llm.calls[2]["messages"][-1]
    assert rejected["is_error"] is True and "Need photos." in rejected["content"]


def test_small_refunds_are_auto_approved() -> None:
    llm = MockLLM([refund_call(15.0), "Refunded."])

    def approver(request):
        raise AssertionError("should not ask a human for a small refund")

    result = main.SupportAgent(llm).run("refund", approver=approver)
    assert result.status == "done" and main.REFUNDS[0]["amount"] == 15.0


def test_safe_tools_never_need_approval() -> None:
    llm = MockLLM([MockLLM.tool_call("get_order", {"order_id": "1234"}), "It was delivered."])
    result = main.SupportAgent(llm).run("status?")  # no approver, but nothing risky: no pause
    assert result.status == "done"
