"""Metrics give the right numbers on hand-checked cases. Offline, no model needed."""

import pytest

from common import MockLLM, tool_result, user
from common.testing import load_example

main = load_example(__file__)

GET = {"name": "get_order", "arguments": {"order_id": "1"}}
REFUND = {"name": "issue_refund", "arguments": {"order_id": "1", "amount": 5.0}}
POLICY = {"name": "get_policy", "arguments": {"topic": "refunds"}}


def test_strict_needs_exact_sequence() -> None:
    assert main.strict_match([GET, REFUND], [GET, REFUND])
    assert not main.strict_match([GET, POLICY, REFUND], [GET, REFUND])
    assert not main.strict_match([REFUND, GET], [GET, REFUND])


def test_in_order_allows_extra_calls_but_not_reordering() -> None:
    assert main.in_order_match([GET, POLICY, REFUND], [GET, REFUND])
    assert not main.in_order_match([REFUND, GET], [GET, REFUND])
    assert not main.in_order_match([GET], [GET, REFUND])


def test_any_order_allows_reordering_but_not_missing_calls() -> None:
    assert main.any_order_match([REFUND, POLICY, GET], [GET, REFUND])
    assert not main.any_order_match([GET, GET], [GET, REFUND])


def test_arguments_matter_unless_switched_off() -> None:
    wrong_amount = {"name": "issue_refund", "arguments": {"order_id": "1", "amount": 50.0}}
    assert not main.strict_match([GET, wrong_amount], [GET, REFUND])
    assert main.strict_match([GET, wrong_amount], [GET, REFUND], with_args=False)


def test_argument_order_inside_a_call_does_not_matter() -> None:
    reordered = {"name": "issue_refund", "arguments": {"amount": 5.0, "order_id": "1"}}
    assert main.strict_match([GET, reordered], [GET, REFUND])


def test_precision_and_recall() -> None:
    assert main.tool_precision_recall([GET, POLICY, REFUND], [GET, REFUND]) == (pytest.approx(2 / 3), 1.0)
    assert main.tool_precision_recall([GET], [GET, REFUND]) == (1.0, 0.5)
    assert main.tool_precision_recall([], []) == (1.0, 1.0)
    assert main.tool_precision_recall([], [GET]) == (0.0, 0.0)


def test_pass_at_k_and_pass_hat_k() -> None:
    # 3 successes in 4 trials
    assert main.pass_at_k(4, 3, 1) == pytest.approx(0.75)
    assert main.pass_hat_k(4, 3, 1) == pytest.approx(0.75)  # identical at k = 1
    assert main.pass_at_k(4, 3, 2) == pytest.approx(1.0)  # any 2 trials include a success
    assert main.pass_hat_k(4, 3, 2) == pytest.approx(3 / 6)  # C(3,2) / C(4,2)
    assert main.pass_hat_k(4, 3, 4) == 0.0
    assert main.pass_at_k(4, 0, 4) == 0.0
    with pytest.raises(ValueError):
        main.pass_at_k(2, 1, 3)


def test_keyword_score_is_partial_credit() -> None:
    assert main.keyword_score("Refunded $25", ["refund", "25"]) == 1.0
    assert main.keyword_score("Refunded $50", ["refund", "25"]) == 0.5
    assert main.exact_match("  Paris ", "paris")


def test_cost_from_tokens() -> None:
    assert main.cost_usd(1_000_000, 0) == pytest.approx(4.0)
    assert main.cost_usd(0, 1_000_000) == pytest.approx(20.0)


def test_recorded_runs_headline_numbers() -> None:
    tasks = main.load_tasks()
    scores = [main.score_run(r, tasks[r["task_id"]]) for r in main.load_runs()]
    assert len(scores) == 12
    assert sum(s["success"] for s in scores) == 8
    rel = main.reliability(scores, ks=[1, 4])
    assert rel[1] == (pytest.approx(2 / 3), pytest.approx(2 / 3))
    assert rel[4] == (pytest.approx(1.0), 0.0)


def test_outcome_and_trajectory_can_disagree() -> None:
    """cancel-order trial 2 skipped the lookup: right end state, wrong path."""
    tasks = main.load_tasks()
    run = next(r for r in main.load_runs() if r["task_id"] == "cancel-order" and r["trial"] == 2)
    s = main.score_run(run, tasks["cancel-order"])
    assert s["success"] and not s["in_order"] and s["recall"] == 0.5


def test_trajectory_from_a_real_agent_conversation() -> None:
    llm = MockLLM([MockLLM.tool_call("get_order", {"order_id": "1"}), "Done."])
    messages = [user("refund order 1")]
    reply = llm.chat(messages)
    messages.append(reply.to_message())
    messages.append(tool_result(reply.tool_calls[0].id, '{"status": "delivered"}'))
    messages.append(llm.chat(messages).to_message())
    assert main.trajectory_from_messages(messages) == [GET]
