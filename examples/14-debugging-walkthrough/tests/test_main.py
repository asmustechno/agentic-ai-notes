"""The broken agent fails on the recorded run, the fixed one passes, and the recording stays as a regression test."""

import json

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_bug_reproduces_with_the_recording() -> None:
    broken = main.BrokenAgent(llm=MockLLM(main.load_recording()))
    assert broken.run(main.GOAL) == "Let me look that up for you."
    assert [e["kind"] for e in broken.trace.events] == ["model", "end"]
    assert main.find_problems(broken.trace) == [
        "step 1: model asked for ['get_order'] but no tool ran (loop stopped early?)"
    ]


def test_regression_recorded_run_answers_with_the_date() -> None:
    """The regression test: the exact replies from the bug report must now produce a real answer."""
    llm = MockLLM(main.load_recording())
    agent = main.Agent(llm=llm)
    answer = agent.run(main.GOAL)
    assert "16 November 2026" in answer
    assert [e["name"] for e in agent.trace.events if e["kind"] == "tool"] == ["get_order", "get_shipping_eta"]
    assert llm.remaining == 0  # every recorded reply was used
    assert main.find_problems(agent.trace) == []


def test_tool_results_reach_the_model() -> None:
    llm = MockLLM(main.load_recording())
    main.Agent(llm=llm).run(main.GOAL)
    third_call = llm.calls[2]["messages"]
    results = [m["content"] for m in third_call if m["role"] == "tool"]
    assert '"tracking_id": "PC-998877"' in results[0] and "2026-11-16" in results[1]


def test_record_then_replay_round_trip(tmp_path) -> None:
    script = [MockLLM.tool_call("get_order", {"order_id": "1234"}, text="Checking."), "Shipped."]
    recorder = main.RecordingLLM(MockLLM(script))
    main.Agent(llm=recorder).run(main.GOAL)
    path = tmp_path / "run.json"
    recorder.save(path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert [r["stop_reason"] for r in saved["replies"]] == ["tool_use", "end_turn"]
    replay = main.load_recording(path)
    assert replay[0].tool_calls[0].arguments == {"order_id": "1234"} and replay[1].text == "Shipped."


def test_find_problems_spots_loops_and_cut_offs() -> None:
    trace = main.Trace()
    for step in range(1, 4):
        trace.add("model", step=step, stop_reason="tool_use", text="", tool_calls=["get_order"])
        trace.add("tool", step=step, name="get_order", arguments={"order_id": "1"}, result="Error", is_error=True)
    trace.add("model", step=4, stop_reason="max_tokens", text="Your ord", tool_calls=[])
    problems = main.find_problems(trace)
    assert any("called 3 times with the same arguments" in p for p in problems)
    assert any("stop_reason=max_tokens" in p for p in problems)


def test_tool_errors_are_flagged_for_the_model() -> None:
    script = [MockLLM.tool_call("get_order", {"order_id": "0000"}), "I can't find that order."]
    llm = MockLLM(script)
    agent = main.Agent(llm=llm)
    agent.run(main.GOAL)
    sent = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"][0]
    assert sent["is_error"] is True
    assert agent.trace.events[1]["is_error"] is True
