"""Checkpointing and resuming after simulated crashes. Offline, with MockLLM and a temporary SQLite file."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from common import MockLLM, ToolCall, tool_result, user
from common.testing import load_example

main = load_example(__file__)

AFTER_SAVE_POINTS = ["saved:1", "tool_ran:get_sales", "tool_saved:get_sales", "saved:2", "tool_ran:send_email", "tool_saved:send_email"]


def crash_then_resume(crash_at: str, db: Path, llm: MockLLM) -> tuple[str, main.Outbox]:
    outbox = main.Outbox()
    store = main.CheckpointStore(db)
    with pytest.raises(main.SimulatedCrash):
        main.ResumableAgent(llm, store, outbox, on_event=main.crash_once_at(crash_at)).run("r1", main.GOAL)
    store.close()
    store = main.CheckpointStore(db)  # "new process": only the file survives
    answer = main.ResumableAgent(llm, store, outbox).run("r1", main.GOAL)
    store.close()
    return answer, outbox


@pytest.mark.parametrize("crash_at", AFTER_SAVE_POINTS)
def test_crash_anywhere_after_a_save_sends_one_email_and_repeats_no_model_call(crash_at: str, tmp_path: Path) -> None:
    llm = MockLLM(main.SCRIPT)
    answer, outbox = crash_then_resume(crash_at, tmp_path / "runs.db", llm)
    assert answer == main.SCRIPT[2]
    assert len(outbox.sent) == 1
    assert len(llm.calls) == 3  # exactly the calls an uninterrupted run makes


def test_crash_before_a_reply_is_saved_costs_one_extra_model_call(tmp_path: Path) -> None:
    llm = MockLLM([main.SCRIPT[0], main.SCRIPT[1], main.SCRIPT[1], main.SCRIPT[2]])
    answer, outbox = crash_then_resume("model_replied:2", tmp_path / "runs.db", llm)
    assert answer == main.SCRIPT[2]
    assert len(llm.calls) == 4  # the lost reply was paid for twice...
    assert len(outbox.sent) == 1  # ...but nothing happened twice


def test_resumed_run_sends_the_saved_conversation(tmp_path: Path) -> None:
    llm = MockLLM(main.SCRIPT)
    crash_then_resume("tool_saved:send_email", tmp_path / "runs.db", llm)
    last = llm.calls[-1]["messages"]
    assert [m["role"] for m in last] == ["user", "assistant", "tool", "assistant", "tool"]
    assert "1284" in last[2]["content"]


def test_rerun_with_the_same_tool_call_id_reuses_the_idempotency_key(tmp_path: Path) -> None:
    llm = MockLLM(main.SCRIPT)
    _, outbox = crash_then_resume("tool_ran:send_email", tmp_path / "runs.db", llm)
    assert len(outbox.keys) == 1 and next(iter(outbox.keys)).startswith("r1:")


def test_finished_run_returns_saved_answer_without_calling_the_model(tmp_path: Path) -> None:
    store = main.CheckpointStore(tmp_path / "runs.db")
    llm = MockLLM(main.SCRIPT)
    main.ResumableAgent(llm, store, main.Outbox()).run("r1", main.GOAL)
    again = MockLLM([])  # would raise if called
    assert main.ResumableAgent(again, store, main.Outbox()).run("r1", main.GOAL) == main.SCRIPT[2]
    assert again.calls == []
    assert store.load("r1").status == "done"


def test_run_that_keeps_crashing_is_marked_failed(tmp_path: Path) -> None:
    db = tmp_path / "runs.db"

    def always_crash(event: str) -> None:
        if event == "tool_ran:get_sales":  # reached again on every resume
            raise main.SimulatedCrash(event)

    for _ in range(4):  # first try + 3 resumes, each dying at the same place
        store = main.CheckpointStore(db)
        with pytest.raises(main.SimulatedCrash):
            main.ResumableAgent(MockLLM(main.SCRIPT), store, main.Outbox(), on_event=always_crash).run("r1", main.GOAL)
        store.close()
    store = main.CheckpointStore(db)
    answer = main.ResumableAgent(MockLLM([]), store, main.Outbox()).run("r1", main.GOAL)
    assert "crashed too many times" in answer
    assert store.load("r1").status == "failed"


def test_step_counter_is_persisted(tmp_path: Path) -> None:
    db = tmp_path / "runs.db"
    store = main.CheckpointStore(db)
    looping = MockLLM([MockLLM.tool_call("get_sales", {"week": "2026-W45"})] * 10)
    agent = main.ResumableAgent(looping, store, main.Outbox(), max_steps=3, on_event=main.crash_once_at("saved:2"))
    with pytest.raises(main.SimulatedCrash):
        agent.run("r1", main.GOAL)
    assert store.load("r1").step == 2
    answer = main.ResumableAgent(looping, store, main.Outbox(), max_steps=3).run("r1", main.GOAL)
    assert answer == "Stopped: step limit reached."
    assert len(looping.calls) == 3  # the limit counted steps from before the crash too


def test_messages_round_trip_through_json() -> None:
    block = SimpleNamespace(model_dump=lambda **_: {"type": "text", "text": "hi"})
    messages = [
        user("hello"),
        {"role": "assistant", "content": "", "tool_calls": [ToolCall("c1", "get_sales", {"week": "W1"})],
         "_raw": {"provider": "anthropic", "content": [block]}},
        tool_result("c1", "{}", is_error=True),
    ]
    back = main.decode_messages(main.encode_messages(messages))
    assert back[1]["tool_calls"] == [ToolCall("c1", "get_sales", {"week": "W1"})]
    assert back[1]["_raw"]["content"] == [{"type": "text", "text": "hi"}]
    assert back[2] == tool_result("c1", "{}", is_error=True)


def test_pending_tool_calls() -> None:
    a, b = ToolCall("a", "get_sales", {}), ToolCall("b", "get_sales", {})
    msgs = [user("x"), {"role": "assistant", "content": "", "tool_calls": [a, b]}, tool_result("a", "1")]
    assert main.ResumableAgent.pending_tool_calls(msgs) == [b]
    assert main.ResumableAgent.pending_tool_calls([user("x")]) == []


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    main.main()
    out = capsys.readouterr().out
    assert out.count("emails actually sent: 1") == 2
    assert "already sent (key run-42:" in out
