"""Orchestrator-workers: the plan decides how many workers run. Offline, with MockLLM."""

import json

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def run(task: str):
    orchestrator = MockLLM([main.mock_orchestrator] * 2)
    worker = MockLLM([main.mock_worker] * 6)
    return main.orchestrate(task, orchestrator, worker), orchestrator, worker


def test_number_of_workers_depends_on_the_task() -> None:
    feature, _, feature_workers = run(main.FEATURE)
    typo, _, typo_workers = run(main.TYPO)
    assert len(feature.plan) == 5 and len(feature_workers.calls) == 5
    assert len(typo.plan) == 1 and len(typo_workers.calls) == 1


def test_each_worker_sees_the_goal_and_only_its_own_subtask() -> None:
    _, _, worker = run(main.FEATURE)
    prompts = [c["messages"][0]["content"] for c in worker.calls]
    assert all(p.startswith(f"Overall goal: {main.FEATURE}") for p in prompts)
    files = sorted(p.split("Your file: ")[1].split("\n")[0] for p in prompts)
    assert files == sorted(s["file"] for s in main.PLANS[main.FEATURE]["subtasks"])
    assert all(c["system"] == main.WORKER_SYSTEM for c in worker.calls)


def test_outputs_keep_plan_order_and_reach_the_synthesiser() -> None:
    result, orchestrator, _ = run(main.FEATURE)
    assert result.worker_outputs[0] == main.WORKER_REPLIES["app/models/user.py"]
    synth = orchestrator.calls[1]
    assert synth["system"] == main.SYNTH_SYSTEM
    assert all(out in synth["messages"][0]["content"] for out in result.worker_outputs)
    assert result.summary.startswith("This change touches 5 files")


def test_invalid_plans_are_rejected_before_any_worker_runs() -> None:
    bad_plans = [
        "Sure! First I will edit the model...",  # not JSON
        json.dumps({"subtasks": []}),  # empty
        json.dumps({"subtasks": [{"file": "/etc/passwd", "instruction": "x"}]}),  # file not allowed
        json.dumps({"subtasks": [{"file": "README.md", "instruction": i} for i in ("a", "b")]}),  # same file twice
        json.dumps({"subtasks": [{"file": "README.md", "instruction": "x"}] * (main.MAX_SUBTASKS + 1)}),
    ]
    for plan in bad_plans:
        worker = MockLLM([])
        with pytest.raises(main.PlanError):
            main.orchestrate("task", MockLLM([plan]), worker)
        assert worker.calls == []
