"""Budget caps are enforced in the loop, the model is warned before the last step, and runs stop gracefully."""

import pytest

from common import MockLLM, Usage
from common.testing import load_example

main = load_example(__file__)


def agent(budget, script=None, clock=None):
    llm = MockLLM(script or [main.researcher] * 30)
    kwargs = {"clock": clock} if clock else {}
    return main.BudgetedAgent(llm=llm, budget=budget, **kwargs), llm


def test_finishes_normally_within_a_generous_budget() -> None:
    a, llm = agent(main.Budget(max_steps=20))
    result = a.run(main.GOAL)
    assert result.stopped_by is None and "6 sources" in result.answer
    assert result.usage["steps"] == 7 == len(llm.calls)


def test_last_step_note_lets_the_model_finish_well() -> None:
    a, llm = agent(main.Budget(max_steps=4))
    result = a.run(main.GOAL)
    assert result.stopped_by is None  # the model answered on its last allowed step
    assert "Partial answer" in result.answer
    assert len(llm.calls) == 4
    assert main.LAST_STEP_NOTE in llm.calls[3]["messages"][-1]["content"]
    assert result.notes == ["step 4: told the model it is the last step"]


def test_step_cap_is_enforced_even_if_the_model_ignores_the_note() -> None:
    stubborn = [MockLLM.tool_call("search", {"query": "more"})] * 10
    a, llm = agent(main.Budget(max_steps=3), script=stubborn)
    result = a.run(main.GOAL)
    assert result.stopped_by == "step limit (3)"
    assert len(llm.calls) == 3
    assert result.answer.startswith("I stopped before finishing")


def test_dollar_cap_stops_before_the_call_that_would_exceed_it() -> None:
    a, llm = agent(main.Budget(max_steps=20, max_dollars=0.004))
    result = a.run(main.GOAL)
    assert result.stopped_by == "dollar limit ($0.004)"
    assert result.usage["dollars"] <= 0.004


def test_time_cap_uses_an_injectable_clock() -> None:
    now = [0.0]

    def clock() -> float:
        now[0] += 10.0  # every look at the clock is 10 seconds later
        return now[0]

    a, llm = agent(main.Budget(max_steps=20, max_seconds=25), clock=clock)
    result = a.run(main.GOAL)
    assert result.stopped_by == "time limit (25s)"
    assert len(llm.calls) < 7


def test_tracker_counts_and_checks_each_limit() -> None:
    t = main.BudgetTracker(main.Budget(max_steps=None, max_input_tokens=1000, max_output_tokens=50))
    t.start()
    t.record(Usage(400, 20))
    assert t.stop_reason(next_input_estimate=500) is None
    assert t.stop_reason(next_input_estimate=700) == "input-token limit (1,000)"
    t.record(Usage(500, 30))
    assert t.stop_reason() == "output-token limit (50)"
    assert t.dollars == pytest.approx((900 * 4 + 50 * 20) / 1e6)
    assert t.summary()["steps"] == 2


def test_is_last_step() -> None:
    t = main.BudgetTracker(main.Budget(max_steps=2))
    assert not t.is_last_step()
    t.record(Usage(1, 1))
    assert t.is_last_step()
