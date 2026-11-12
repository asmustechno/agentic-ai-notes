"""The AutoGen (legacy) version of the weather agent. Offline, with ReplayChatCompletionClient.

Skipped unless `autogen-agentchat` is installed (see ../requirements.txt).
"""

import asyncio

import pytest

pytest.importorskip("autogen_agentchat")

from autogen_agentchat.messages import ToolCallSummaryMessage  # noqa: E402
from autogen_core.models import SystemMessage  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def test_agent_calls_tools_then_answers() -> None:
    client = main.replay_client()
    result = asyncio.run(main.run(main.build_agent(client)))
    assert result.messages[-1].to_text() == main.ANSWER
    assert main.trace(result) == [
        'tool call:   get_weather({"city": "Paris"})',
        'tool call:   get_weather({"city": "Rome"})',
        'tool result: {"city": "Paris", "temp_c": 14}',
        'tool result: {"city": "Rome", "temp_c": 19}',
        'tool call:   calculator({"expression": "19 - 14"})',
        "tool result: 5",
    ]
    assert len(client.create_calls) == 3


def test_system_message_and_tools_are_sent() -> None:
    client = main.replay_client()
    asyncio.run(main.run(main.build_agent(client)))
    first = client.create_calls[0]
    assert isinstance(first["messages"][0], SystemMessage) and first["messages"][0].content == main.INSTRUCTIONS
    assert [t["name"] for t in first["tools"]] == ["get_weather", "calculator"]  # tool schemas, as dicts
    assert first["tools"][0]["parameters"]["required"] == ["city"]


def test_default_max_tool_iterations_stops_after_one_round() -> None:
    """A classic AutoGen surprise: by default the agent runs ONE round of tools and returns a summary."""
    client = main.replay_client()
    agent = main.AssistantAgent("default_agent", model_client=client, tools=[main.get_weather, main.calculator])
    result = asyncio.run(agent.run(task=main.GOAL))
    assert isinstance(result.messages[-1], ToolCallSummaryMessage)
    assert len(client.create_calls) == 1


def test_plain_tool_functions() -> None:
    assert main.get_weather("Rome") == '{"city": "Rome", "temp_c": 19}'
    assert main.calculator("1 / 0").startswith("Error")
