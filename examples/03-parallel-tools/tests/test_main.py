"""Parallel tool calls run concurrently, keep their order, and go back in the right shape. Offline."""

from __future__ import annotations

import asyncio
import threading
import time

from common import MockLLM, ToolCall
from common.llm import to_anthropic_messages, to_openai_messages
from common.testing import load_example

main = load_example(__file__)


def calls(n: int) -> list[ToolCall]:
    return [ToolCall(id=f"id_{i}", name="t", arguments={"i": i}) for i in range(n)]


def test_calls_really_run_at_the_same_time() -> None:
    barrier = threading.Barrier(3, timeout=5)  # only passes if all 3 calls are running at once

    def t(i: int) -> str:
        barrier.wait()
        return str(i)

    results = main.run_parallel(calls(3), {"t": t})
    assert [r["content"] for r in results] == ["0", "1", "2"]
    assert not any(r["is_error"] for r in results)


def test_results_keep_call_order_even_when_they_finish_out_of_order() -> None:
    def t(i: int) -> str:
        time.sleep(0.05 * (3 - i))  # the first call finishes last
        return f"result {i}"

    results = main.run_parallel(calls(4), {"t": t})
    assert [r["tool_call_id"] for r in results] == ["id_0", "id_1", "id_2", "id_3"]
    assert [r["content"] for r in results] == ["result 0", "result 1", "result 2", "result 3"]


def test_asyncio_version_is_concurrent_and_ordered() -> None:
    barrier = threading.Barrier(3, timeout=5)

    def t(i: int) -> str:
        barrier.wait()
        return str(i)

    results = asyncio.run(main.run_parallel_async(calls(3), {"t": t}))
    assert [r["tool_call_id"] for r in results] == ["id_0", "id_1", "id_2"]


def test_one_failure_does_not_stop_the_others() -> None:
    batch = [ToolCall("a", "get_weather", {"city": "Paris"}), ToolCall("b", "get_weather", {"city": "Atlantis"}),
             ToolCall("c", "nope", {})]
    results = main.run_parallel(batch, main.TOOLS)
    assert [r["is_error"] for r in results] == [False, True, True]
    assert "unknown city 'Atlantis'" in results[1]["content"]
    assert "unknown tool 'nope'" in results[2]["content"]


def test_parallel_is_faster_than_sequential() -> None:
    batch = MockLLM.tool_calls(main.CALLS).tool_calls
    start = time.perf_counter()
    main.run_parallel(batch, main.TOOLS)
    parallel = time.perf_counter() - start
    assert parallel < 2 * main.LATENCY_SECONDS  # sequential would take 3 x latency


def test_anthropic_gets_all_results_in_one_user_message() -> None:
    llm = MockLLM(main.script())
    answer = main.run_agent(llm, main.GOAL)
    assert answer.startswith("Rome is the warmest")
    history = llm.calls[1]["messages"]
    anthropic = to_anthropic_messages(history)
    assert [m["role"] for m in anthropic] == ["user", "assistant", "user"]
    assert [b["type"] for b in anthropic[-1]["content"]] == ["tool_result"] * 3
    ids = [b["tool_use_id"] for b in anthropic[-1]["content"]]
    assert ids == [b["id"] for b in anthropic[1]["content"] if b["type"] == "tool_use"]  # same order as the calls


def test_openai_gets_one_tool_message_per_result() -> None:
    llm = MockLLM(main.script())
    main.run_agent(llm, main.GOAL)
    openai = to_openai_messages(llm.calls[1]["messages"])
    assert [m["role"] for m in openai] == ["user", "assistant", "tool", "tool", "tool"]
    assert len(openai[1]["tool_calls"]) == 3


def test_empty_batch() -> None:
    assert main.run_parallel([], main.TOOLS) == []
