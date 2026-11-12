"""The Paris-vs-Rome weather agent from 1.5, rebuilt with AutoGen AgentChat (legacy).

AutoGen is archived: Microsoft points new users to Microsoft Agent Framework
(see ../11-agent-framework). This example exists so you can read old AutoGen
code and compare it side by side when migrating.

    python main.py               # from this folder (offline, ReplayChatCompletionClient)
    python 11-autogen/main.py    # from examples/

    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # OpenAI (needs OPENAI_API_KEY)

Offline, the agent uses AutoGen's own `ReplayChatCompletionClient`, which
replays a list of scripted model results; AssistantAgent's tool loop is real.
Needs `pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.4-microsoft-autogen-and-agent-framework.md.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import operator
import os
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass

from autogen_agentchat.agents import AssistantAgent  # noqa: E402
from autogen_agentchat.base import TaskResult  # noqa: E402
from autogen_agentchat.messages import ToolCallExecutionEvent, ToolCallRequestEvent  # noqa: E402
from autogen_core import EVENT_LOGGER_NAME, FunctionCall  # noqa: E402
from autogen_core.models import ChatCompletionClient, CreateResult, ModelInfo, RequestUsage  # noqa: E402
from autogen_ext.models.replay import ReplayChatCompletionClient  # noqa: E402

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def get_weather(city: str) -> str:
    """Get the current temperature in °C for one city, e.g. 'Paris'."""
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'."""

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

_USAGE = RequestUsage(prompt_tokens=0, completion_tokens=0)


def _calls(*calls: tuple[str, dict[str, str], str]) -> CreateResult:
    return CreateResult(
        finish_reason="function_calls",
        content=[FunctionCall(id=i, name=n, arguments=json.dumps(a)) for n, a, i in calls],
        usage=_USAGE,
        cached=False,
    )


def replay_client() -> ReplayChatCompletionClient:
    """Scripted model results, replayed in order. model_info says the "model" can call functions."""
    logging.getLogger(EVENT_LOGGER_NAME).setLevel(logging.ERROR)  # hide the replay client's token-count warnings
    return ReplayChatCompletionClient(
        [
            _calls(("get_weather", {"city": "Paris"}, "call_1"), ("get_weather", {"city": "Rome"}, "call_2")),
            _calls(("calculator", {"expression": "19 - 14"}, "call_3")),
            ANSWER,
        ],
        model_info=ModelInfo(vision=False, function_calling=True, json_output=False, family="unknown", structured_output=False),
    )


def choose_client() -> ChatCompletionClient:
    if (os.getenv("LLM_PROVIDER") or "mock").lower() == "openai":
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(model=os.environ["OPENAI_MODEL"])
    return replay_client()


def build_agent(client: ChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="travel_assistant",
        model_client=client,
        tools=[get_weather, calculator],  # plain functions; AutoGen builds the schemas
        system_message=INSTRUCTIONS,
        max_tool_iterations=6,  # the default is 1: one round of tools, then stop
    )


def trace(result: TaskResult) -> list[str]:
    lines = []
    for message in result.messages:
        if isinstance(message, ToolCallRequestEvent):
            lines += [f"tool call:   {c.name}({c.arguments})" for c in message.content]
        elif isinstance(message, ToolCallExecutionEvent):
            lines += [f"tool result: {r.content}" for r in message.content]
    return lines


async def run(agent: AssistantAgent, goal: str = GOAL) -> TaskResult:
    return await agent.run(task=goal)


def main() -> None:
    result = asyncio.run(run(build_agent(choose_client())))
    print(f"Goal: {GOAL}\n")
    print("\n".join(trace(result)))
    print(f"\nAnswer: {result.messages[-1].to_text()}")


if __name__ == "__main__":
    main()
