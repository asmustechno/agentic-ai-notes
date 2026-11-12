"""Concurrent tool execution takes about as long as the slowest tool, and keeps results in order."""

import time

from common.testing import load_example

main = load_example(__file__)


def fast_tools(monkeypatch) -> None:
    monkeypatch.setattr(main, "DELAYS", {"get_weather": 0.04, "get_flights": 0.07, "get_hotels": 0.05})


def test_concurrent_is_faster_than_sequential(monkeypatch) -> None:
    fast_tools(monkeypatch)
    calls = main.REPLY.tool_calls
    _, t_seq = main.timed(lambda: main.run_sequential(calls))
    _, t_con = main.timed(lambda: main.run_concurrent(calls))
    assert t_seq >= 0.15
    assert t_con < t_seq * 0.8


def test_results_keep_the_call_order_and_ids(monkeypatch) -> None:
    fast_tools(monkeypatch)
    calls = main.REPLY.tool_calls
    results = main.run_concurrent(calls)
    assert [m["tool_call_id"] for m in results] == [c.id for c in calls]
    assert results[1]["content"].startswith("get_flights result")
    assert all(m["role"] == "tool" for m in results)


def test_stream_yields_every_word() -> None:
    start = time.perf_counter()
    chunks = list(main.fake_stream("a b c", ttft=0.01, tokens_per_second=1000))
    assert "".join(chunks).split() == ["a", "b", "c"]
    assert time.perf_counter() - start >= 0.01
