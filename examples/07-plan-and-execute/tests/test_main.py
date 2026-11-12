"""Plan-and-execute: the plan is validated, run in dependency order, and each step sees only what it needs."""

import json

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_happy_path_answer_and_call_count() -> None:
    llm = MockLLM(main.SCRIPT)
    agent = main.PlanAndExecute(llm)
    answer = agent.run(main.GOAL)
    assert "EUR 1,200" in answer
    assert len(llm.calls) == len(main.SCRIPT)  # 1 plan + 4 steps x 2 calls + 1 answer
    assert llm.calls[0]["system"] == main.PLANNER_SYSTEM and llm.calls[0]["tools"] is None  # the planner has no tools


def test_steps_run_in_dependency_order() -> None:
    steps = main.parse_plan(main.PLAN_JSON)
    assert main.batches(steps) == [["s1", "s3"], ["s2"], ["s4"]]
    agent = main.PlanAndExecute(MockLLM(main.SCRIPT))
    agent.run(main.GOAL)
    finished = [line.split()[1].rstrip(":") for line in agent.log if line.startswith("done")]
    assert finished == ["s1", "s3", "s2", "s4"]


def test_executor_gets_only_its_dependencies_results() -> None:
    llm = MockLLM(main.SCRIPT)
    main.PlanAndExecute(llm).run(main.GOAL)
    s4_prompt = llm.calls[7]["messages"][0]["content"]  # first executor call for s4
    assert "Your step (s4)" in s4_prompt
    assert "- s2: Casa Azul (v1) is available" in s4_prompt and "- s3: Lunch costs EUR 300." in s4_prompt
    assert "- s1:" not in s4_prompt  # s4 does not depend on s1 directly


def test_a_failed_step_stops_the_run() -> None:
    script = main.SCRIPT[:1] + [MockLLM.tool_call("search_venues", {"city": "Porto", "min_capacity": 12}),
                                "FAILED: no venues found in Porto."]
    agent = main.PlanAndExecute(MockLLM(script))
    assert agent.run(main.GOAL).startswith("Stopped: step s1 failed")


@pytest.mark.parametrize(
    "plan, message",
    [
        ("not json", "not valid JSON"),
        (json.dumps({"steps": []}), "at least one step"),
        (json.dumps({"steps": [{"id": "a", "task": "x"}, {"id": "a", "task": "y"}]}), "unique"),
        (json.dumps({"steps": [{"id": "a", "task": "x", "depends_on": ["zz"]}]}), "unknown steps"),
        (json.dumps({"steps": [{"id": "a", "task": "x", "depends_on": ["b"]},
                               {"id": "b", "task": "y", "depends_on": ["a"]}]}), "cycle"),
    ],
)
def test_bad_plans_are_rejected(plan: str, message: str) -> None:
    with pytest.raises(main.PlanError, match=message):
        main.parse_plan(plan)


def test_fenced_json_is_accepted() -> None:
    assert len(main.parse_plan(f"```json\n{main.PLAN_JSON}\n```")) == 4


def test_tools() -> None:
    assert [v["id"] for v in json.loads(main.search_venues("lisbon", 16))] == ["v2", "v3"]
    assert json.loads(main.check_availability("v1", "2026-12-04"))["available"] is False
    assert main.check_availability("v9", "2026-12-04").startswith("Error")
    assert main.calculator("900 + 12 * 25") == "1200"
    assert main.calculator("import os").startswith("Error")
