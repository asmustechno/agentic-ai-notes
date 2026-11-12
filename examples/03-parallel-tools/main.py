"""Parallel tool calls: the model asks for several tools in one turn, and we run them at the same time.

Shows three things:
  1. running the calls one by one vs concurrently (threads, and asyncio),
  2. keeping the results in the same order as the calls, matched by id,
  3. sending every result back in ONE message (Anthropic) or one message per result (OpenAI).

    python main.py                      # from this folder
    python 03-parallel-tools/main.py    # from examples/

Read alongside docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolCall, get_llm, tool_result, user  # noqa: E402
from common.llm import to_anthropic_messages, to_openai_messages  # noqa: E402

# --------------------------------------------------------------------------- a slow tool

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
LATENCY_SECONDS = 0.3  # pretend each call is a slow network request


def get_weather(city: str) -> str:
    """Current temperature in °C (fake data, with a fake network delay)."""
    time.sleep(LATENCY_SECONDS)
    if city.lower() not in FAKE_WEATHER:
        raise LookupError(f"unknown city {city!r}")
    return json.dumps({"city": city, "temp_c": FAKE_WEATHER[city.lower()]})


WEATHER_SPEC = {
    "name": "get_weather",
    "description": "Get the current temperature in °C for ONE city. To compare cities, call it once per city "
                   "in the same turn.",
    "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}
TOOLS: dict[str, Callable[..., str]] = {"get_weather": get_weather}

# --------------------------------------------------------------------------- running a batch of calls


def run_one(call: ToolCall, tools: dict[str, Callable[..., str]]) -> Message:
    """Run one call. A failure becomes an error result; it never stops the other calls."""
    try:
        if call.name not in tools:
            raise LookupError(f"unknown tool {call.name!r}")
        return tool_result(call.id, tools[call.name](**call.arguments))
    except Exception as exc:
        return tool_result(call.id, f"Error: {exc}", is_error=True)


def run_sequential(calls: list[ToolCall], tools: dict[str, Callable[..., str]]) -> list[Message]:
    return [run_one(call, tools) for call in calls]


def run_parallel(calls: list[ToolCall], tools: dict[str, Callable[..., str]], max_workers: int = 8) -> list[Message]:
    """Run every call at once in a thread pool. pool.map returns results in the order of `calls`."""
    if not calls:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(calls))) as pool:
        return list(pool.map(lambda call: run_one(call, tools), calls))


async def run_parallel_async(calls: list[ToolCall], tools: dict[str, Callable[..., str]]) -> list[Message]:
    """The asyncio version. asyncio.gather also keeps the order of its arguments.

    asyncio.to_thread runs our blocking function in a thread. If your tools are
    already `async def` (for example using httpx.AsyncClient), await them directly.
    """
    return list(await asyncio.gather(*(asyncio.to_thread(run_one, call, tools) for call in calls)))


# --------------------------------------------------------------------------- the agent loop


def run_agent(llm: LLM, goal: str, *, parallel: bool = True, max_steps: int = 5) -> str:
    messages: list[Message] = [user(goal)]
    for _ in range(max_steps):
        reply = llm.chat(messages, tools=[WEATHER_SPEC])
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text
        results = (run_parallel if parallel else run_sequential)(reply.tool_calls, TOOLS)
        messages.extend(results)  # in call order; the wrapper merges them into ONE Anthropic user message
    return "Stopped: step limit reached."


GOAL = "Which is warmest right now: Paris, Rome or London?"
CALLS = [("get_weather", {"city": "Paris"}), ("get_weather", {"city": "Rome"}), ("get_weather", {"city": "London"})]


def script() -> list[Any]:
    return [MockLLM.tool_calls(CALLS), "Rome is the warmest at 19°C (Paris 14°C, London 11°C)."]


def main() -> None:
    batch = MockLLM.tool_calls(CALLS).tool_calls
    print(f"The model asked for {len(batch)} tool calls in one turn:")
    for call in batch:
        print(f"  {call.id}: {call.name}({call.arguments})")

    print("\n1) One by one vs at the same time")
    for label, runner in [("sequential", run_sequential), ("threads   ", run_parallel)]:
        start = time.perf_counter()
        runner(batch, TOOLS)
        print(f"  {label}: {time.perf_counter() - start:.1f}s")
    start = time.perf_counter()
    asyncio.run(run_parallel_async(batch, TOOLS))
    print(f"  asyncio   : {time.perf_counter() - start:.1f}s")

    print("\n2) How the results go back to each provider")
    history = [user(GOAL), {"role": "assistant", "content": "", "tool_calls": batch}, *run_parallel(batch, TOOLS)]
    anthropic = to_anthropic_messages(history)
    openai = to_openai_messages(history)
    print(f"  Anthropic: {len(anthropic)} messages; the last is ONE user message with "
          f"{len(anthropic[-1]['content'])} tool_result blocks:")
    for block in anthropic[-1]["content"]:
        print(f"    {{'type': 'tool_result', 'tool_use_id': '{block['tool_use_id']}', 'content': '{block['content']}'}}")
    print(f"  OpenAI: {len(openai)} messages; the last {len(batch)} are separate role='tool' messages:")
    for msg in openai[-len(batch):]:
        print(f"    {{'role': 'tool', 'tool_call_id': '{msg['tool_call_id']}', 'content': '{msg['content']}'}}")

    print("\n3) The full agent run")
    print(f"  Answer: {run_agent(get_llm(mock_responses=script()), GOAL)}")


if __name__ == "__main__":
    main()
