"""The Paris-vs-Rome weather agent from 1.5, rebuilt with Microsoft Agent Framework.

    python main.py                         # from this folder (offline, scripted chat client)
    python 11-agent-framework/main.py      # from examples/

    LLM_PROVIDER=anthropic python main.py                     # Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # OpenAI (needs OPENAI_API_KEY)

Agent Framework has no ready-made fake model, so offline we write a tiny chat
client: `BaseChatClient` (the documented extension point) plus the framework's
`FunctionInvocationLayer`, which is the part that runs tools and loops. Only
the model's replies are scripted. Needs `pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.4-microsoft-autogen-and-agent-framework.md.
"""

from __future__ import annotations

import ast
import asyncio
import json
import operator
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass

from agent_framework import (  # noqa: E402
    Agent,
    AgentResponse,
    BaseChatClient,
    ChatResponse,
    Content,
    FunctionInvocationLayer,
    Message,
    SupportsChatGetResponse,
)
from pydantic import Field  # noqa: E402

# --------------------------------------------------------------------------- tools: plain functions

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def get_weather(city: Annotated[str, Field(description="City name, e.g. 'Paris'.")]) -> str:
    """Get the current temperature in °C for one city."""
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


def calculator(expression: Annotated[str, Field(description="For example '19 - 14'.")]) -> str:
    """Evaluate an arithmetic expression with + - * / and numbers."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        raise ValueError("only numbers and + - * / are allowed")

    try:
        return str(ev(ast.parse(expression, mode="eval").body))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"Error: {exc}"


INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
ANSWER = "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C."

# --------------------------------------------------------------------------- the offline "model"


def scripted_reply(messages: Sequence[Message]) -> Message:
    """Play the model: pick the next reply from how many tool results it has seen."""
    results_seen = sum(c.type == "function_result" for m in messages for c in m.contents)
    if results_seen == 0:
        return Message(
            "assistant",
            [
                Content.from_function_call("call_1", "get_weather", arguments={"city": "Paris"}),
                Content.from_function_call("call_2", "get_weather", arguments={"city": "Rome"}),
            ],
        )
    if results_seen == 2:
        return Message("assistant", [Content.from_function_call("call_3", "calculator", arguments={"expression": "19 - 14"})])
    return Message("assistant", [ANSWER])


class ScriptedChatClient(FunctionInvocationLayer, BaseChatClient):
    """A chat client whose replies come from a Python function. It records every request."""

    def __init__(self, reply: Callable[[Sequence[Message]], Message] = scripted_reply, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def _inner_get_response(self, *, messages: Sequence[Message], stream: bool, options: Mapping[str, Any], **kwargs: Any):  # type: ignore[no-untyped-def]
        if stream:
            raise NotImplementedError("this offline client only supports agent.run() without streaming")

        async def respond() -> ChatResponse:
            self.calls.append({"messages": list(messages), "options": dict(options)})
            return ChatResponse(messages=[self.reply(messages)], response_id=f"scripted-{len(self.calls)}")

        return respond()


def choose_client() -> SupportsChatGetResponse:
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        from agent_framework.anthropic import AnthropicClient

        return AnthropicClient(model=(os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"))
    if provider == "openai":
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(model=os.environ["OPENAI_MODEL"])
    return ScriptedChatClient()


# --------------------------------------------------------------------------- the agent


def build_agent(client: SupportsChatGetResponse) -> Agent:
    # Plain functions become tools; the docstring and Annotated descriptions build the schema.
    return Agent(client=client, name="TravelAssistant", instructions=INSTRUCTIONS, tools=[get_weather, calculator])


def trace(response: AgentResponse) -> list[str]:
    lines = []
    for message in response.messages:
        for c in message.contents:
            if c.type == "function_call":
                args = c.arguments if isinstance(c.arguments, str) else json.dumps(c.arguments)
                lines.append(f"tool call:   {c.name}({args})")
            elif c.type == "function_result":
                lines.append(f"tool result: {c.result}")
    return lines


def main() -> None:
    response = asyncio.run(build_agent(choose_client()).run(GOAL))
    print(f"Goal: {GOAL}\n")
    print("\n".join(trace(response)))
    print(f"\nAnswer: {response.text}")


if __name__ == "__main__":
    main()
