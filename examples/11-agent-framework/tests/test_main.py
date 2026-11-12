"""The Microsoft Agent Framework version of the weather agent. Offline, with a scripted chat client.

Skipped unless `agent-framework` is installed (see ../requirements.txt).
"""

import asyncio

import pytest

pytest.importorskip("agent_framework")

from agent_framework import Content, Message  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def run(client):  # type: ignore[no-untyped-def]
    return asyncio.run(main.build_agent(client).run(main.GOAL))


def test_agent_calls_tools_then_answers() -> None:
    client = main.ScriptedChatClient()
    response = run(client)
    assert response.text == main.ANSWER
    assert len(client.calls) == 3
    assert main.trace(response) == [
        'tool call:   get_weather({"city": "Paris"})',
        'tool call:   get_weather({"city": "Rome"})',
        'tool result: {"city": "Paris", "temp_c": 14}',
        'tool result: {"city": "Rome", "temp_c": 19}',
        'tool call:   calculator({"expression": "19 - 14"})',
        "tool result: 5",
    ]


def test_instructions_and_tool_schemas_are_sent() -> None:
    client = main.ScriptedChatClient()
    run(client)
    options = client.calls[0]["options"]
    assert options["instructions"] == main.INSTRUCTIONS
    assert [t.name for t in options["tools"]] == ["get_weather", "calculator"]
    schema = options["tools"][0].parameters()
    assert schema["required"] == ["city"]
    assert schema["properties"]["city"]["description"] == "City name, e.g. 'Paris'."


def test_both_tool_results_go_back_in_one_message() -> None:
    client = main.ScriptedChatClient()
    run(client)
    roles = [(m.role, [c.type for c in m.contents]) for m in client.calls[1]["messages"]]
    assert roles[-1] == ("tool", ["function_result", "function_result"])


def test_max_iterations_stops_a_runaway_loop() -> None:
    def always_a_tool(messages):  # type: ignore[no-untyped-def]
        return Message("assistant", [Content.from_function_call("c", "calculator", arguments={"expression": "1+1"})])

    client = main.ScriptedChatClient(always_a_tool, function_invocation_configuration={"max_iterations": 3})
    run(client)
    # 3 tool rounds, then one final request made with tools switched off so the model must answer.
    assert len(client.calls) == 4
    assert client.calls[-1]["options"].get("tool_choice") == "none"


def test_plain_tool_functions() -> None:
    assert main.get_weather("Atlantis") == "Unknown city: Atlantis"
    assert main.calculator("2 * (3 + 4)") == "14"
