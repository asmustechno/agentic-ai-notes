"""Routing, policy in code, and handoff to a human. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def run_case(i: int) -> tuple:
    message, script = main.CASES[i]
    llm, desk = MockLLM(script), main.Desk()
    return main.handle(llm, desk, message), llm, desk


def test_order_status_is_answered_by_the_agent() -> None:
    outcome, llm, desk = run_case(0)
    assert outcome.resolved_by == "agent" and "15 November" in outcome.reply
    assert [t["name"] for t in llm.calls[1]["tools"]] == ["lookup_order", "handoff_to_human"]  # no refund tool
    assert desk.tickets == []


def test_big_refund_is_refused_in_code_and_handed_off_with_summary() -> None:
    outcome, llm, desk = run_case(1)
    assert outcome.resolved_by == "human"
    assert desk.refunds == []  # the model asked for 189 EUR; the code said no
    refusal = llm.calls[3]["messages"][-1]
    assert refusal["is_error"] and "need a person" in refusal["content"]
    assert "A-200" in desk.tickets[0]["summary"]


def test_asking_for_a_human_skips_the_model_entirely() -> None:
    outcome, llm, desk = run_case(2)
    assert outcome.resolved_by == "human" and llm.calls == []
    assert desk.tickets[0]["reason"] == "asked for a human"


def test_small_refund_goes_through() -> None:
    script = [
        '{"intent": "refund", "confidence": 0.9}',
        MockLLM.tool_call("issue_refund", {"order_id": "A-100", "amount_eur": 10, "reason": "Scratched"}),
        "Done: 10 EUR is on its way back to you.",
    ]
    desk = main.Desk()
    outcome = main.handle(MockLLM(script), desk, "Lamp A-100 is scratched, can I get 10 EUR back?")
    assert outcome.resolved_by == "agent"
    assert desk.refunds == [{"order_id": "A-100", "amount_eur": 10, "reason": "Scratched"}]


def test_low_confidence_or_bad_json_routes_to_safe_tool_set() -> None:
    for router_reply in ['{"intent": "refund", "confidence": 0.3}', "refund please", '{"intent": "hack"}']:
        llm = MockLLM([router_reply, "Could you tell me your order number?"])
        outcome = main.handle(llm, main.Desk(), "money back??")
        assert outcome.intent == "other"
        assert [t["name"] for t in llm.calls[1]["tools"]] == ["handoff_to_human"]


def test_tool_outside_intent_is_refused() -> None:
    llm = MockLLM(['{"intent": "order_status", "confidence": 0.9}',
                   MockLLM.tool_call("issue_refund", {"order_id": "A-100", "amount_eur": 5, "reason": "x"}), "ok"])
    desk = main.Desk()
    main.handle(llm, desk, "where is A-100")
    assert desk.refunds == []


def test_stuck_agent_is_handed_off_by_the_loop_guard() -> None:
    bad = MockLLM.tool_call("lookup_order", {"order_id": "Z-999"})
    llm = MockLLM(['{"intent": "order_status", "confidence": 0.9}', bad, bad, bad])
    desk = main.Desk()
    outcome = main.handle(llm, desk, "where is Z-999")
    assert outcome.resolved_by == "human" and desk.tickets[0]["reason"] == "agent stuck"


def test_hard_rules() -> None:
    assert main.hard_rule("I will contact my lawyer") == "legal or chargeback"
    assert main.hard_rule("Where is my order?") is None
