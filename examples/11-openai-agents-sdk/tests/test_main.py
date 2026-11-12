"""The OpenAI Agents SDK version of the weather agent. Offline, with the SDK's ScriptedModel.

Skipped unless `openai-agents` is installed (see ../requirements.txt).
"""

import asyncio

import pytest

pytest.importorskip("agents")

from agents import Agent, ToolCallOutputItem  # noqa: E402
from agents.exceptions import MaxTurnsExceeded  # noqa: E402
from agents.testing import ScriptedModel, function_call  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def test_agent_calls_tools_then_answers() -> None:
    model = main.scripted_model()
    result = asyncio.run(main.run(main.build_agent(model)))
    assert result.final_output == main.ANSWER
    outputs = [item.output for item in result.new_items if isinstance(item, ToolCallOutputItem)]
    assert outputs == ['{"city": "Paris", "temp_c": 14}', '{"city": "Rome", "temp_c": 19}', "5"]
    assert len(model.calls) == 3
    model.assert_complete()


def test_instructions_and_tool_schemas_are_sent_to_the_model() -> None:
    model = main.scripted_model()
    asyncio.run(main.run(main.build_agent(model)))
    first = model.first_call
    assert first is not None
    assert first.system_instructions == main.INSTRUCTIONS
    assert [t.name for t in first.tools] == ["get_weather", "calculator"]
    assert first.tools[0].params_json_schema["required"] == ["city"]


def test_tool_results_go_back_to_the_model() -> None:
    model = main.scripted_model()
    asyncio.run(main.run(main.build_agent(model)))
    second_input = model.calls[1].input
    outputs = [item for item in second_input if item.get("type") == "function_call_output"]
    assert [o["call_id"] for o in outputs] == ["call_1", "call_2"]


def test_runner_stops_at_max_turns() -> None:
    looping = ScriptedModel(
        [[function_call("calculator", {"expression": "1+1"}, call_id=f"c{i}")] for i in range(10)]
    )
    with pytest.raises(MaxTurnsExceeded):
        asyncio.run(main.run(main.build_agent(looping)))


def test_handoff_from_a_triage_agent() -> None:
    """A triage agent hands the conversation to the travel agent. The handoff is a tool named transfer_to_<agent>."""
    triage_model = ScriptedModel([[function_call("transfer_to_travel_assistant", {}, call_id="h1")]])
    triage = Agent(
        name="Triage",
        instructions="Route travel questions to the travel assistant.",
        model=triage_model,
        handoffs=[main.build_agent(main.scripted_model())],
    )
    result = asyncio.run(main.run(triage))
    assert [h.tool_name for h in triage_model.first_call.handoffs] == ["transfer_to_travel_assistant"]
    assert result.last_agent.name == "Travel assistant"
    assert result.final_output == main.ANSWER


def test_plain_tool_functions() -> None:
    assert main.lookup_weather("Rome") == '{"city": "Rome", "temp_c": 19}'
    assert main.lookup_weather("Atlantis") == "Unknown city: Atlantis"
    assert main.evaluate("19 - 14") == "5"
    assert main.evaluate("__import__('os')").startswith("Error")
