"""Where the time goes in an agent run, and two ways to win it back: concurrent tools and streaming.

    python main.py                  # from this folder
    python 16-latency/main.py       # from examples/

Offline, the "model" and the "tools" are fake and simply sleep, so the timings are illustrative.
Each step of an agent costs roughly:

    model time (time to first token + output tokens / output speed) + tool time + your own code

Read alongside docs/16-cost-and-performance/16.4-latency-optimisation.md.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import Message, MockLLM, ToolCall, tool_result  # noqa: E402

# --------------------------------------------------------------------------- fake tools with realistic delays

DELAYS = {"get_weather": 0.4, "get_flights": 0.7, "get_hotels": 0.5}


def make_tool(name: str) -> Callable[..., str]:
    def tool(**kwargs: Any) -> str:
        time.sleep(DELAYS[name])
        return f"{name} result for {kwargs}"

    return tool


TOOLS: dict[str, Callable[..., str]] = {name: make_tool(name) for name in DELAYS}

# One model reply that asks for three independent tools at once (parallel tool calls).
REPLY = MockLLM.tool_calls([
    ("get_weather", {"city": "Lisbon"}),
    ("get_flights", {"to": "LIS", "date": "2026-12-04"}),
    ("get_hotels", {"city": "Lisbon", "nights": 3}),
])


def run_sequential(calls: list[ToolCall]) -> list[Message]:
    """The easy way: one tool after another. Total time = the sum of the tool times."""
    return [tool_result(c.id, TOOLS[c.name](**c.arguments)) for c in calls]


def run_concurrent(calls: list[ToolCall], max_workers: int = 8) -> list[Message]:
    """Run independent tools at the same time. Total time = the slowest tool. Order of results is kept."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(lambda c: TOOLS[c.name](**c.arguments), calls))
    # All results for one turn go back together, in one message on Anthropic (the wrapper merges them).
    return [tool_result(c.id, r) for c, r in zip(calls, results)]


# --------------------------------------------------------------------------- streaming: time to first token


def fake_stream(text: str, ttft: float = 0.6, tokens_per_second: float = 40.0) -> Iterator[str]:
    """Pretend to stream a reply: a wait before the first token, then a steady rate of tokens."""
    time.sleep(ttft)
    for word in text.split(" "):
        yield word + " "
        time.sleep(1 / tokens_per_second)


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - start


def main() -> None:
    calls = REPLY.tool_calls
    print("1) Three independent tool calls from one model reply")
    seq, t_seq = timed(lambda: run_sequential(calls))
    con, t_con = timed(lambda: run_concurrent(calls))
    assert [m["tool_call_id"] for m in seq] == [m["tool_call_id"] for m in con]
    print(f"   sequential: {t_seq:.1f} s   (0.4 + 0.7 + 0.5)")
    print(f"   concurrent: {t_con:.1f} s   (the slowest tool, 0.7)")

    print("\n2) Streaming a 60-word answer")
    answer = " ".join(["word"] * 60)
    start = time.perf_counter()
    first = None
    for i, _chunk in enumerate(fake_stream(answer)):
        if i == 0:
            first = time.perf_counter() - start
    total = time.perf_counter() - start
    print(f"   first words on screen after {first:.1f} s; whole answer after {total:.1f} s")
    print("   without streaming the user stares at nothing for the whole time.")


if __name__ == "__main__":
    main()
