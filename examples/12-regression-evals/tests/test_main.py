"""Regression tests that run on every pull request: offline, deterministic, free.

They replay model replies recorded from a real run, so they test everything
around the model: the loop, the tools, the state changes and the graders.
"""

import json
from pathlib import Path

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)

CASES = {c["id"]: c for c in main.load_cases()}
KNOWN_FAILURES = {"refund-over-limit"}  # tracked bug: the agent refunds instead of escalating


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_recorded_case(case_id: str) -> None:
    if case_id in KNOWN_FAILURES:
        pytest.xfail("known failure, see baseline.json")  # stays visible in the test report
    result = main.run_case(CASES[case_id], main.replay_llm(case_id))
    assert result["passed"], result["problems"]


def test_known_failure_still_fails_for_the_documented_reason() -> None:
    result = main.run_case(CASES["refund-over-limit"], main.replay_llm("refund-over-limit"))
    assert not result["passed"]
    assert "'3333': 900.0" in result["problems"][0]


def test_agent_sends_the_policy_and_all_tools() -> None:
    llm = main.replay_llm("track-order")
    main.run_agent(llm, CASES["track-order"]["input"], main.Store())
    assert "$500" in llm.calls[0]["system"]
    assert [t["name"] for t in llm.calls[0]["tools"]] == ["get_order", "issue_refund", "cancel_order",
                                                           "escalate_to_human"]


def test_tool_errors_reach_the_model_as_errors() -> None:
    llm = main.replay_llm("cancel-shipped")
    main.run_agent(llm, CASES["cancel-shipped"]["input"], main.Store())
    error = [m for m in llm.calls[2]["messages"] if m["role"] == "tool"][-1]
    assert error["is_error"] and "cannot be cancelled" in error["content"]


def test_grader_checks_end_state_and_answer() -> None:
    case = CASES["refund-damaged"]
    good = main.Store(refunds={"1234": 25.0})
    assert main.grade(case, "Refunded $25.", good) == []
    assert main.grade(case, "Refunded.", good) == ["answer is missing '25'"]
    assert len(main.grade(case, "Refunded $25.", main.Store())) == 1  # nothing was refunded


def test_stale_recordings_are_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "SYSTEM", main.SYSTEM + " Be extra polite.")
    with pytest.raises(main.StaleRecording):
        main.replay_llm("track-order")


def test_recording_round_trip(tmp_path: Path) -> None:
    real = MockLLM([MockLLM.tool_call("get_order", {"order_id": "5678"}), "Due Thursday."])
    recorder = main.RecordingLLM(real)
    main.run_agent(recorder, "Where is 5678?", main.Store())
    recorder.save(tmp_path / "track-order.json")
    saved = json.loads((tmp_path / "track-order.json").read_text(encoding="utf-8"))
    assert saved["prompt_fingerprint"] == main.prompt_fingerprint()
    replay = main.replay_llm("track-order", recorded_dir=tmp_path)
    answer, _ = main.run_agent(replay, "Where is 5678?", main.Store())
    assert answer == "Due Thursday."


def test_regressions_compare_against_baseline() -> None:
    results = [{"id": "a", "passed": False}, {"id": "b", "passed": False}, {"id": "c", "passed": True}]
    assert main.regressions(results, {"a": True, "b": False, "c": True}) == ["a"]


def test_exit_code_fails_below_threshold_or_on_regression(capsys: pytest.CaptureFixture[str]) -> None:
    results = [{"id": "a", "tags": ["x"], "passed": True, "problems": [], "trial": 1},
               {"id": "b", "tags": ["x"], "passed": False, "problems": ["bad"], "trial": 1}]
    assert main.report(results, threshold=0.5, baseline={}) == 0
    assert main.report(results, threshold=0.9, baseline={}) == 1  # 50% < 90%
    assert main.report(results, threshold=0.5, baseline={"b": True}) == 1  # b used to pass
    assert "RESULT: FAIL" in capsys.readouterr().out


def test_full_offline_run_passes() -> None:
    assert main.main([]) == 0
