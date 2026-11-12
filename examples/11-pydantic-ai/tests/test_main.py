"""The Pydantic AI version of the weather agent. Offline, with FunctionModel and TestModel.

Skipped unless `pydantic-ai-slim` is installed (see ../requirements.txt).
"""

import pytest

pytest.importorskip("pydantic_ai")

from pydantic_ai import (  # noqa: E402
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UsageLimits,
    capture_run_messages,
    models,
)
from pydantic_ai.exceptions import UsageLimitExceeded  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)
models.ALLOW_MODEL_REQUESTS = False  # a safety net: any real model call in these tests fails


def test_agent_calls_tools_then_answers() -> None:
    result = main.agent.run_sync(main.GOAL, model=FunctionModel(main.scripted_reply))
    assert result.output == main.ANSWER
    assert result.usage.requests == 3
    assert main.trace(result.all_messages()) == [
        'tool call:   get_weather({"city":"Paris"})',
        'tool call:   get_weather({"city":"Rome"})',
        'tool result: {"city": "Paris", "temp_c": 14}',
        'tool result: {"city": "Rome", "temp_c": 19}',
        'tool call:   calculator({"expression":"19 - 14"})',
        "tool result: 5",
    ]


def test_tool_schemas_come_from_type_hints_and_docstrings() -> None:
    seen: list[AgentInfo] = []

    def spy(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info)
        return ModelResponse(parts=[TextPart("ok")])

    main.agent.run_sync("hi", model=FunctionModel(spy))
    tools = {t.name: t for t in seen[0].function_tools}
    assert set(tools) == {"get_weather", "calculator"}
    weather = tools["get_weather"]
    assert weather.description == "Get the current temperature in °C for one city."
    assert weather.parameters_json_schema["properties"]["city"]["type"] == "string"
    assert weather.parameters_json_schema["properties"]["city"]["description"] == "City name, e.g. 'Paris'."


def test_bad_tool_arguments_are_sent_back_for_a_retry() -> None:
    """Pydantic validates the model's arguments. A wrong one goes back to the model as a retry prompt."""

    def wrong_then_right(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        replies = sum(isinstance(m, ModelResponse) for m in messages)
        if replies == 0:
            return ModelResponse(parts=[ToolCallPart("get_weather", {"town": "Paris"})])  # wrong argument name
        return ModelResponse(parts=[TextPart("done")])

    with capture_run_messages() as messages:
        main.agent.run_sync("Paris?", model=FunctionModel(wrong_then_right))
    returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    assert len(returns) == 1
    assert returns[0].outcome == "retried" and returns[0].retry.cause == "validation_error"
    assert "Field required" in returns[0].model_response_str()  # the model is told what was wrong


def test_usage_limits_stop_a_runaway_loop() -> None:
    def always_a_tool(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart("calculator", {"expression": "1+1"})])

    with pytest.raises(UsageLimitExceeded):
        main.agent.run_sync("loop", model=FunctionModel(always_a_tool), usage_limits=UsageLimits(request_limit=3))


def test_test_model_calls_every_tool() -> None:
    """TestModel needs no script: it calls every tool once with made-up valid arguments."""
    result = main.agent.run_sync(main.GOAL, model=TestModel())
    called = [line for line in main.trace(result.all_messages()) if line.startswith("tool call")]
    assert {c.split("(")[0] for c in called} == {"tool call:   get_weather", "tool call:   calculator"}
