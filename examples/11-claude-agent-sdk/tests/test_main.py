"""The Claude Agent SDK version of the weather agent.

The SDK has no offline model: a real run needs the Claude Code runtime (bundled
with the package) and an API key. So the offline tests check the tools and the
options; the one end-to-end test runs only when you opt in with
CLAUDE_AGENT_SDK_LIVE=1 and ANTHROPIC_API_KEY (it calls the real API, which costs money).

Skipped unless `claude-agent-sdk` is installed (see ../requirements.txt).
"""

import asyncio
import os

import pytest

pytest.importorskip("claude_agent_sdk")

from claude_agent_sdk import SdkMcpTool  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def call(tool: SdkMcpTool, args: dict) -> dict:  # type: ignore[type-arg]
    return asyncio.run(tool.handler(args))


def test_tools_are_sdk_mcp_tools_with_schemas() -> None:
    assert isinstance(main.get_weather, SdkMcpTool)
    assert main.get_weather.name == "get_weather"
    assert main.get_weather.input_schema == {"city": str}
    assert main.get_weather.annotations.model_dump(by_alias=True)["readOnlyHint"] is True


def test_tool_handlers_return_mcp_content() -> None:
    assert call(main.get_weather, {"city": "Rome"}) == {"content": [{"type": "text", "text": '{"city": "Rome", "temp_c": 19}'}]}
    assert call(main.calculator, {"expression": "19 - 14"})["content"][0]["text"] == "5"


def test_tool_failures_are_reported_as_errors() -> None:
    unknown = call(main.get_weather, {"city": "Atlantis"})
    assert unknown["is_error"] is True and "Unknown city" in unknown["content"][0]["text"]
    assert call(main.calculator, {"expression": "__import__('os')"})["is_error"] is True


def test_options_restrict_the_agent_to_our_tools() -> None:
    options = main.build_options()
    assert options.tools == []  # built-in Claude Code tools removed
    assert options.allowed_tools == ["mcp__travel__get_weather", "mcp__travel__calculator"]
    assert options.mcp_servers["travel"]["type"] == "sdk"
    assert options.system_prompt == main.INSTRUCTIONS
    assert options.setting_sources == []
    assert options.max_turns == 6


def test_offline_replay_uses_the_real_handlers() -> None:
    lines = asyncio.run(main.replay_locally())
    assert lines[-1] == 'tool call:   mcp__travel__calculator({"expression": "19 - 14"}) -> 5'


@pytest.mark.skipif(
    not (os.getenv("CLAUDE_AGENT_SDK_LIVE") == "1" and os.getenv("ANTHROPIC_API_KEY")),
    reason="live test: set CLAUDE_AGENT_SDK_LIVE=1 and ANTHROPIC_API_KEY to run it",
)
def test_live_run_answers_rome() -> None:
    answer, lines = asyncio.run(main.run())
    assert "Rome" in answer
    assert any("mcp__travel__get_weather" in line for line in lines)
