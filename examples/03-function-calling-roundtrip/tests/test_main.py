"""The round-trip payloads have each provider's exact shape. Offline, no network."""

from __future__ import annotations

import json

from common import MockLLM, user
from common.testing import load_example

main = load_example(__file__)
TOOLS = [main.WEATHER_TOOL]


def test_anthropic_request_shape() -> None:
    body = main.anthropic_request([user(main.QUESTION)], TOOLS)
    assert body["system"] == main.SYSTEM  # a top-level field
    assert body["tools"][0]["input_schema"]["required"] == ["city"]  # the schema is called input_schema
    assert body["messages"] == [{"role": "user", "content": main.QUESTION}]


def test_openai_request_shape() -> None:
    body = main.openai_request([user(main.QUESTION)], TOOLS)
    assert body["messages"][0] == {"role": "system", "content": main.SYSTEM}  # system is the first message
    tool = body["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["parameters"] == main.WEATHER_TOOL["input_schema"]  # the schema is called parameters


def test_both_responses_parse_to_the_same_tool_call() -> None:
    a = main.parse_anthropic(main.ANTHROPIC_TOOL_USE_RESPONSE)
    o = main.parse_openai(main.OPENAI_TOOL_CALLS_RESPONSE)
    assert a.stop_reason == o.stop_reason == "tool_use"
    assert (a.tool_calls[0].name, a.tool_calls[0].arguments) == (o.tool_calls[0].name, o.tool_calls[0].arguments)
    assert a.tool_calls[0].id == "toolu_01A09q90qw90lq" and o.tool_calls[0].id == "call_abc123"


def test_openai_arguments_arrive_as_a_json_string() -> None:
    raw = main.OPENAI_TOOL_CALLS_RESPONSE["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
    assert isinstance(raw, str) and json.loads(raw) == {"city": "Paris"}


def test_tool_result_shapes() -> None:
    a = main.parse_anthropic(main.ANTHROPIC_TOOL_USE_RESPONSE)
    history = [user(main.QUESTION), a.to_message(), *main.run_tool_calls(a)]

    anthropic_msgs = main.to_anthropic_messages(history)
    assert anthropic_msgs[-1]["role"] == "user"  # tool results travel in a USER message
    block = anthropic_msgs[-1]["content"][0]
    assert block["type"] == "tool_result" and block["tool_use_id"] == "toolu_01A09q90qw90lq"

    openai_msgs = main.to_openai_messages(history, main.SYSTEM)
    assert openai_msgs[-1]["role"] == "tool" and openai_msgs[-1]["tool_call_id"] == "toolu_01A09q90qw90lq"
    assert json.loads(openai_msgs[-2]["tool_calls"][0]["function"]["arguments"]) == {"city": "Paris"}


def test_round_trip_through_the_wrapper() -> None:
    llm = MockLLM(main.SCRIPT)
    assert main.round_trip_with(llm) == "It's 18°C and sunny in Paris right now."
    second = llm.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "tool"]
    assert json.loads(second[2]["content"])["temp"] == 18
    assert llm.calls[0]["tools"] == TOOLS


def test_get_weather() -> None:
    assert json.loads(main.get_weather("Paris", "fahrenheit"))["temp"] == 64
