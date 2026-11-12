"""The function-calling round trip, shown as the exact JSON each provider sends and receives.

One question ("What's the weather in Paris?"), one tool (get_weather), and
four steps: request -> tool call -> tool result -> answer. For each step we
print the Anthropic Messages API payload and the OpenAI Chat Completions
payload, built by the same converters the shared wrapper uses.

    python main.py                                  # from this folder
    python 03-function-calling-roundtrip/main.py    # from examples/

Read alongside docs/03-tools-and-function-calling/03.3-how-function-calling-works.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402
from common.llm import from_anthropic, from_openai, to_anthropic_messages, to_openai_messages, to_openai_tools  # noqa: E402

SYSTEM = "You are a helpful assistant. Use tools for live data."
QUESTION = "What's the weather in Paris?"
WEATHER_TOOL: ToolSpec = {
    "name": "get_weather",
    "description": "Get the current weather for one city. Call this whenever the user asks about weather.",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Paris'."},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Defaults to celsius."},
        },
        "required": ["city"],
    },
}


def get_weather(city: str, unit: str = "celsius") -> str:
    """Fake weather data for the demo."""
    return json.dumps({"city": city, "temp": 18 if unit == "celsius" else 64, "unit": unit, "sky": "sunny"})


# --------------------------------------------------------------------------- step 1: the request


def anthropic_request(messages: list[Message], tools: list[ToolSpec]) -> dict[str, Any]:
    """The body of POST /v1/messages (Anthropic)."""
    return {"model": "claude-opus-5-5", "max_tokens": 1024, "system": SYSTEM, "tools": tools,
            "messages": to_anthropic_messages(messages)}


def openai_request(messages: list[Message], tools: list[ToolSpec]) -> dict[str, Any]:
    """The body of POST /v1/chat/completions (OpenAI). The system prompt is the first message."""
    return {"model": "YOUR_OPENAI_MODEL", "max_completion_tokens": 1024, "tools": to_openai_tools(tools),
            "messages": to_openai_messages(messages, SYSTEM)}


# --------------------------------------------------------------------------- step 2: the model asks for a tool
# Sample responses in each provider's real shape (IDs shortened). In a live run the SDK returns these.

ANTHROPIC_TOOL_USE_RESPONSE = {
    "id": "msg_01Aq9w938a90dw8q",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-5-5",
    "content": [
        {"type": "text", "text": "I'll check the current weather in Paris."},
        {"type": "tool_use", "id": "toolu_01A09q90qw90lq", "name": "get_weather", "input": {"city": "Paris"}},
    ],
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 412, "output_tokens": 61},
}

OPENAI_TOOL_CALLS_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "choices": [{
        "index": 0,
        "finish_reason": "tool_calls",
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_abc123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"},
            }],
        },
    }],
    "usage": {"prompt_tokens": 98, "completion_tokens": 18},
}


def as_object(data: Any) -> Any:
    """Turn parsed JSON into attribute-style objects, like the SDKs return (tool inputs stay dicts)."""
    if isinstance(data, dict):
        return NS(**{k: v if k == "input" else as_object(v) for k, v in data.items()})
    if isinstance(data, list):
        return [as_object(v) for v in data]
    return data


def parse_anthropic(raw: dict[str, Any]) -> LLMResponse:
    resp = from_anthropic(as_object(raw))
    resp.raw = None  # replay from our neutral message, not the sample object
    return resp


def parse_openai(raw: dict[str, Any]) -> LLMResponse:
    return from_openai(as_object(raw))


# --------------------------------------------------------------------------- steps 3 and 4: result and answer


def run_tool_calls(reply: LLMResponse) -> list[Message]:
    """Run every requested tool and build one result message per call."""
    tools = {"get_weather": get_weather}
    return [tool_result(call.id, tools[call.name](**call.arguments)) for call in reply.tool_calls]


def pretty(obj: Any, indent: int = 0, width: int = 100) -> str:
    """JSON, indented, but with any part that fits on one line kept on one line."""
    flat = json.dumps(obj, ensure_ascii=False)
    if len(flat) + indent <= width or not isinstance(obj, (dict, list)) or not obj:
        return flat
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k)}: {pretty(v, indent + 2, width)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    items = [f"{inner}{pretty(v, indent + 2, width)}" for v in obj]
    return "[\n" + ",\n".join(items) + f"\n{pad}]"


def show(title: str, payload: Any) -> None:
    print(f"--- {title}")
    print(pretty(payload))
    print()


def round_trip_with(llm: LLM) -> str:
    """The same round trip through the shared wrapper (MockLLM offline, or a real provider)."""
    history: list[Message] = [user(QUESTION)]
    reply = llm.chat(history, system=SYSTEM, tools=[WEATHER_TOOL])
    history.append(reply.to_message())
    history += run_tool_calls(reply)
    return llm.chat(history, system=SYSTEM, tools=[WEATHER_TOOL]).text


SCRIPT = [
    MockLLM.tool_call("get_weather", {"city": "Paris"}, text="I'll check the current weather in Paris."),
    "It's 18°C and sunny in Paris right now.",
]


def main() -> None:
    history: list[Message] = [user(QUESTION)]

    print("=" * 70 + "\nSTEP 1  Your code sends the question and the tool definitions\n")
    show("Anthropic request body", anthropic_request(history, [WEATHER_TOOL]))
    show("OpenAI request body", openai_request(history, [WEATHER_TOOL]))

    print("=" * 70 + "\nSTEP 2  The model replies with a tool call instead of an answer\n")
    show("Anthropic response (stop_reason: tool_use)", ANTHROPIC_TOOL_USE_RESPONSE)
    show("OpenAI response (finish_reason: tool_calls)", OPENAI_TOOL_CALLS_RESPONSE)
    a_reply, o_reply = parse_anthropic(ANTHROPIC_TOOL_USE_RESPONSE), parse_openai(OPENAI_TOOL_CALLS_RESPONSE)
    print("Both parse to the same neutral shape:")
    print(f"  anthropic -> {a_reply.tool_calls[0]}  stop_reason={a_reply.stop_reason}")
    print(f"  openai    -> {o_reply.tool_calls[0]}  stop_reason={o_reply.stop_reason}\n")

    print("=" * 70 + "\nSTEP 3  Your code runs the tool and sends the result back\n")
    a_history = history + [a_reply.to_message(), *run_tool_calls(a_reply)]
    o_history = history + [o_reply.to_message(), *run_tool_calls(o_reply)]
    show("Anthropic: the last two messages of the next request", to_anthropic_messages(a_history)[-2:])
    show("OpenAI: the last two messages of the next request", to_openai_messages(o_history, SYSTEM)[-2:])

    print("=" * 70 + "\nSTEP 4  The model reads the result and answers\n")
    print(f"Answer: {round_trip_with(get_llm(mock_responses=SCRIPT))}")


if __name__ == "__main__":
    main()
