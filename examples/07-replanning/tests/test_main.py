"""Re-planning keeps finished work, revises the rest, and stops within its limits. Offline, with MockLLM."""

import json

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_failure_triggers_a_replan_that_succeeds() -> None:
    llm = MockLLM(main.SCRIPT)
    agent = main.ReplanningAgent(llm)
    answer = agent.run(main.GOAL)
    assert "LX Loft" in answer and "EUR 1,400" in answer
    assert "FAILED s2: Casa Azul (v1) is already booked on 2026-12-04." in agent.log
    assert list(agent.finished) == ["s1", "s3", "r1", "r2"]  # s2 failed; s4 was replaced by r2
    assert len(llm.calls) == len(main.SCRIPT)


def test_replanner_sees_finished_work_and_the_failure() -> None:
    llm = MockLLM(main.SCRIPT)
    main.ReplanningAgent(llm).run(main.GOAL)
    replan_call = next(c for c in llm.calls if c["system"] == main.REPLANNER_SYSTEM)
    prompt = replan_call["messages"][0]["content"]
    assert "- s1 (Find Lisbon venues" in prompt and "- s3 (Work out lunch" in prompt
    assert "FAILED step s2" in prompt and "already booked" in prompt
    assert replan_call["tools"] is None


def test_finished_steps_are_not_rerun() -> None:
    llm = MockLLM(main.SCRIPT)
    agent = main.ReplanningAgent(llm)
    agent.run(main.GOAL)
    searches = [line for line in agent.log if "search_venues" in line]
    assert len(searches) == 1  # s1's result was reused by r1


def test_new_plan_may_depend_on_finished_steps_only() -> None:
    steps = main.parse_plan(main.REPLAN_JSON, finished={"s1", "s3"})
    assert main.batches(steps, {"s1", "s3"}) == [["r1"], ["r2"]]
    with pytest.raises(main.PlanError, match="unknown"):
        main.parse_plan(main.REPLAN_JSON, finished={"s1"})  # r2 needs s3
    with pytest.raises(main.PlanError, match="new, unique"):
        main.parse_plan(main.PLAN_JSON, finished={"s1"})  # reusing a finished id


def _all_booked_script(replans: int) -> list:
    """Every venue is booked: each plan fails at the availability check."""
    script = [main.PLAN_JSON,
              MockLLM.tool_call("search_venues", {"city": "Lisbon", "min_capacity": 12}), "DONE: v1, v2, v3.",
              MockLLM.tool_call("calculator", {"expression": "12 * 25"}), "DONE: EUR 300.",
              MockLLM.tool_call("check_availability", {"venue_id": "v1", "date": "2026-12-04"}),
              "FAILED: v1 is booked."]
    for i, venue in enumerate(["v2", "v3"][:replans]):
        script += [json.dumps({"steps": [{"id": f"r{i + 1}", "task": f"Check {venue}", "depends_on": ["s1"]}]}),
                   MockLLM.tool_call("check_availability", {"venue_id": venue, "date": "2026-12-04"}),
                   f"FAILED: {venue} is booked."]
    return script


def test_gives_up_after_max_replans(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "BOOKED", {(v, "2026-12-04") for v in ("v1", "v2", "v3")})
    llm = MockLLM(_all_booked_script(replans=2))
    answer = main.ReplanningAgent(llm, max_replans=2).run(main.GOAL)
    assert answer == "Gave up after 2 re-plans. Last failure: v3 is booked."
    assert sum(c["system"] == main.REPLANNER_SYSTEM for c in llm.calls) == 2


def test_planner_can_give_up() -> None:
    script = _all_booked_script(replans=0) + [json.dumps({"give_up": "No venue fits the budget."})]
    answer = main.ReplanningAgent(MockLLM(script)).run(main.GOAL)
    assert answer == "Gave up: No venue fits the budget."


def test_same_failure_twice_stops_the_loop() -> None:
    same = json.dumps({"steps": [{"id": "r1", "task": "Check the cheapest venue is free on 2026-12-04",
                                  "depends_on": ["s1"]}]})
    script = _all_booked_script(replans=0)
    script[-1] = "FAILED: booked."
    script += [same, MockLLM.tool_call("check_availability", {"venue_id": "v1", "date": "2026-12-04"}),
               "FAILED: booked."]
    answer = main.ReplanningAgent(MockLLM(script), max_replans=5).run(main.GOAL)
    assert answer.startswith("Gave up: step r1 failed the same way twice")
