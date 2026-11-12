"""Tests for the shared LLM wrapper and MockLLM. No network or API key needed."""

from __future__ import annotations

from types import SimpleNamespace as NS
from typing import Any

import pytest

from common import AnthropicLLM, LLMResponse, MockLLM, MockLLMExhausted, OpenAILLM, ToolCall, get_llm, tool_result, user
from common.llm import from_anthropic, from_openai, to_anthropic_messages, to_openai_messages, to_openai_tools

WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}


# --------------------------------------------------------------------------- MockLLM


def test_mock_returns_script_in_order_and_records_calls() -> None:
    llm = MockLLM([MockLLM.tool_call("get_weather", {"city": "Paris"}), "18°C and sunny."])

    first = llm.chat([user("Weather in Paris?")], tools=[WEATHER_TOOL], system="Be brief.")
    assert first.stop_reason == "tool_use"
    assert first.tool_calls[0].name == "get_weather"
    assert first.tool_calls[0].arguments == {"city": "Paris"}

    second = llm.chat([user("Weather in Paris?"), first.to_message(), tool_result(first.tool_calls[0].id, "18C")])
    assert second.text == "18°C and sunny."
    assert second.stop_reason == "end_turn"

    assert len(llm.calls) == 2
    assert llm.calls[0]["system"] == "Be brief."
    assert llm.calls[0]["tools"] == [WEATHER_TOOL]
    assert llm.calls[1]["messages"][-1]["role"] == "tool"
    assert llm.remaining == 0


def test_mock_raises_when_script_runs_out() -> None:
    llm = MockLLM(["only one"])
    llm.chat([user("hi")])
    with pytest.raises(MockLLMExhausted):
        llm.chat([user("again")])


def test_mock_default_reply_when_script_runs_out() -> None:
    llm = MockLLM([], default="fallback")
    assert llm.chat([user("hi")]).text == "fallback"


def test_mock_callable_sees_conversation() -> None:
    llm = MockLLM([lambda messages: f"You said: {messages[-1]['content']}"])
    assert llm.chat([user("ping")]).text == "You said: ping"


def test_mock_records_a_snapshot_of_messages() -> None:
    llm = MockLLM(["a", "b"])
    history = [user("first")]
    llm.chat(history)
    history.append(user("second"))
    llm.chat(history)
    assert len(llm.calls[0]["messages"]) == 1  # not mutated by later appends


def test_mock_parallel_tool_calls_have_unique_ids() -> None:
    resp = MockLLM.tool_calls([("a", {}), ("b", {})])
    assert [c.name for c in resp.tool_calls] == ["a", "b"]
    assert resp.tool_calls[0].id != resp.tool_calls[1].id


def test_mock_estimates_usage() -> None:
    resp = MockLLM(["x" * 40]).chat([user("y" * 80)])
    assert resp.usage.input_tokens == 20
    assert resp.usage.output_tokens == 10


# --------------------------------------------------------------------------- factory


def test_get_llm_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    llm = get_llm(mock_responses=["scripted"])
    assert isinstance(llm, MockLLM)
    assert llm.chat([user("hi")]).text == "scripted"


def test_get_llm_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        get_llm("nope")


def test_openai_requires_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        OpenAILLM(client=object())


# --------------------------------------------------------------------------- Anthropic conversion

CONVERSATION = [
    user("Weather in Paris and Rome?"),
    {
        "role": "assistant",
        "content": "Checking both.",
        "tool_calls": [
            ToolCall("t1", "get_weather", {"city": "Paris"}),
            ToolCall("t2", "get_weather", {"city": "Rome"}),
        ],
    },
    tool_result("t1", "18C"),
    tool_result("t2", "City not found", is_error=True),
]


def test_anthropic_tool_results_share_one_user_message() -> None:
    out = to_anthropic_messages(CONVERSATION)
    assert [m["role"] for m in out] == ["user", "assistant", "user"]
    assert out[1]["content"][0] == {"type": "text", "text": "Checking both."}
    assert out[1]["content"][1]["type"] == "tool_use"
    results = out[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]
    assert "is_error" not in results[0]
    assert results[1]["is_error"] is True


def test_anthropic_replays_raw_content_unchanged() -> None:
    raw_blocks = [NS(type="thinking", thinking="", signature="sig"), NS(type="text", text="hi")]
    msg = {"role": "assistant", "content": "hi", "tool_calls": [], "_raw": {"provider": "anthropic", "content": raw_blocks}}
    out = to_anthropic_messages([user("q"), msg])
    assert out[1]["content"] is raw_blocks


def _fake_anthropic_response() -> Any:
    return NS(
        content=[
            NS(type="thinking", thinking=""),
            NS(type="text", text="Let me check."),
            NS(type="tool_use", id="toolu_1", name="get_weather", input={"city": "Paris"}),
        ],
        stop_reason="tool_use",
        usage=NS(input_tokens=100, output_tokens=20),
    )


def test_from_anthropic_parses_text_and_tool_calls() -> None:
    resp = from_anthropic(_fake_anthropic_response())
    assert resp.text == "Let me check."
    assert resp.tool_calls == [ToolCall("toolu_1", "get_weather", {"city": "Paris"})]
    assert resp.stop_reason == "tool_use"
    assert (resp.usage.input_tokens, resp.usage.output_tokens) == (100, 20)
    assert resp.to_message()["_raw"]["content"][0].type == "thinking"


class _Recorder:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return _fake_anthropic_response()


def test_anthropic_llm_uses_server_side_fallback_for_supported_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_FALLBACKS", raising=False)
    plain, beta = _Recorder(), _Recorder()
    client = NS(messages=plain, beta=NS(messages=beta))
    llm = AnthropicLLM("claude-opus-5-5", client=client)
    llm.chat([user("hi")], system="sys", tools=[WEATHER_TOOL], max_tokens=500)
    assert beta.kwargs["fallbacks"] == "default"
    assert beta.kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert beta.kwargs["system"] == "sys"
    assert beta.kwargs["tools"] == [WEATHER_TOOL]
    assert beta.kwargs["max_tokens"] == 500
    assert "temperature" not in beta.kwargs
    assert plain.kwargs == {}


def test_anthropic_llm_plain_endpoint_when_fallbacks_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_FALLBACKS", "off")
    plain, beta = _Recorder(), _Recorder()
    llm = AnthropicLLM("claude-opus-5-5", client=NS(messages=plain, beta=NS(messages=beta)))
    llm.chat([user("hi")])
    assert "fallbacks" not in plain.kwargs
    assert beta.kwargs == {}


# --------------------------------------------------------------------------- OpenAI conversion


def test_openai_messages_and_tools() -> None:
    out = to_openai_messages(CONVERSATION, system="Be brief.")
    assert out[0] == {"role": "system", "content": "Be brief."}
    assert out[2]["tool_calls"][1]["function"] == {"name": "get_weather", "arguments": '{"city": "Rome"}'}
    assert out[3] == {"role": "tool", "tool_call_id": "t1", "content": "18C"}
    assert out[4]["content"] == "Error: City not found"

    tools = to_openai_tools([WEATHER_TOOL])
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["parameters"] == WEATHER_TOOL["input_schema"]


def test_from_openai_parses_tool_calls_and_bad_json() -> None:
    raw = NS(
        choices=[
            NS(
                finish_reason="tool_calls",
                message=NS(
                    content=None,
                    refusal=None,
                    tool_calls=[
                        NS(id="c1", type="function", function=NS(name="get_weather", arguments='{"city": "Paris"}')),
                        NS(id="c2", type="function", function=NS(name="get_weather", arguments='{"city": ')),
                    ],
                ),
            )
        ],
        usage=NS(prompt_tokens=50, completion_tokens=10),
    )
    resp = from_openai(raw)
    assert resp.stop_reason == "tool_use"
    assert resp.tool_calls[0].arguments == {"city": "Paris"}
    assert resp.tool_calls[1].error is not None
    assert resp.usage.input_tokens == 50
    assert isinstance(resp, LLMResponse)
