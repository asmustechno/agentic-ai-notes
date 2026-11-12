"""The LlamaIndex version of the weather agent. Offline, with MockFunctionCallingLLM.

Skipped unless `llama-index-core` is installed (see ../requirements.txt).
"""

import asyncio
from typing import Any

import pytest

pytest.importorskip("llama_index.core")

from llama_index.core.llms import ChatMessage, MessageRole, MockFunctionCallingLLM  # noqa: E402
from llama_index.core.tools import FunctionTool  # noqa: E402
from workflows.errors import WorkflowRuntimeError  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def recording_llm() -> tuple[MockFunctionCallingLLM, list[dict[str, Any]]]:
    """The example's scripted model, plus a record of what the agent sent on each call."""
    calls: list[dict[str, Any]] = []

    def reply(messages, **kwargs):  # type: ignore[no-untyped-def]
        calls.append({"messages": list(messages), "tools": kwargs.get("tools") or []})
        return main.scripted_reply(messages, **kwargs)

    return MockFunctionCallingLLM(response_generator=reply), calls


def test_agent_calls_tools_then_answers() -> None:
    answer, lines = asyncio.run(main.run(main.build_agent(MockFunctionCallingLLM(response_generator=main.scripted_reply))))
    assert answer == main.ANSWER
    assert lines == [
        'tool call:   get_weather({"city": "Paris"})',
        'tool call:   get_weather({"city": "Rome"})',
        'tool result: {"city": "Paris", "temp_c": 14}',
        'tool result: {"city": "Rome", "temp_c": 19}',
        'tool call:   calculator({"expression": "19 - 14"})',
        "tool result: 5",
    ]


def test_system_prompt_tools_and_results_reach_the_model() -> None:
    llm, calls = recording_llm()
    asyncio.run(main.run(main.build_agent(llm)))
    assert len(calls) == 3
    first = calls[0]["messages"]
    assert first[0].role == MessageRole.SYSTEM and first[0].content == main.INSTRUCTIONS
    assert [t.metadata.name for t in calls[0]["tools"]] == ["get_weather", "calculator"]
    tool_msgs = [m for m in calls[1]["messages"] if m.role == MessageRole.TOOL]
    assert len(tool_msgs) == 2 and '"temp_c": 19' in tool_msgs[1].content


def test_max_iterations_stops_a_runaway_loop() -> None:
    def always_a_tool(messages, **kwargs):  # type: ignore[no-untyped-def]
        return ChatMessage(role=MessageRole.ASSISTANT, blocks=[main._call("calculator", {"expression": "1+1"}, "c")])

    agent = main.build_agent(MockFunctionCallingLLM(response_generator=always_a_tool))
    with pytest.raises(WorkflowRuntimeError, match="Max iterations"):
        asyncio.run(main.run(agent, max_iterations=3))


def test_plain_functions_become_tools() -> None:
    tool = FunctionTool.from_defaults(main.get_weather)
    assert tool.metadata.name == "get_weather"
    assert "current temperature" in tool.metadata.description
    assert tool.metadata.get_parameters_dict()["required"] == ["city"]
    assert main.calculator("1 / 0").startswith("Error")
