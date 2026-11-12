"""The Paris-vs-Rome weather agent from 1.5, rebuilt with the OpenAI Agents SDK.

    python main.py                          # from this folder (offline, scripted model)
    python 11-openai-agents-sdk/main.py     # from examples/

    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # a real OpenAI model

Offline, the agent uses the SDK's own test double, `agents.testing.ScriptedModel`,
so the real Runner loop, tool schemas and tool execution all run; only the
model's replies are scripted. Needs `pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.5-openai-agents-sdk.md.
"""

from __future__ import annotations

import ast
import asyncio
import json
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

from agents import (  # noqa: E402
    Agent,
    ItemHelpers,
    MessageOutputItem,
    RunConfig,
    Runner,
    RunResult,
    ToolCallItem,
    ToolCallOutputItem,
)
from agents.decorators import tool  # noqa: E402
from agents.models.interface import Model  # noqa: E402
from agents.testing import ScriptedModel, assistant_message, function_call  # noqa: E402

# --------------------------------------------------------------------------- tools (same as examples/01-anatomy-of-an-agent)

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}

_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def lookup_weather(city: str) -> str:
    """Current temperature for a city, in °C (fake data for the demo)."""
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


def evaluate(expression: str) -> str:
    """Evaluate + - * / arithmetic safely (no eval())."""

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


# The SDK reads the function name, type hints and docstring to build each tool's JSON Schema.
@tool
def get_weather(city: str) -> str:
    """Get the current temperature in °C for one city.

    Args:
        city: City name, e.g. 'Paris'.
    """
    return lookup_weather(city)


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'.

    Args:
        expression: The expression to evaluate.
    """
    return evaluate(expression)


# --------------------------------------------------------------------------- the agent

INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
ANSWER = "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C."


def scripted_model() -> ScriptedModel:
    """The model's three replies, scripted: two parallel tool calls, one calculator call, the answer."""
    return ScriptedModel(
        [
            [
                function_call("get_weather", {"city": "Paris"}, call_id="call_1"),
                function_call("get_weather", {"city": "Rome"}, call_id="call_2"),
            ],
            [function_call("calculator", {"expression": "19 - 14"}, call_id="call_3")],
            [assistant_message(ANSWER)],
        ]
    )


def build_agent(model: Model | str) -> Agent:
    """Model, instructions and tools: three of the five parts. Runner provides the loop."""
    return Agent(
        name="Travel assistant",
        instructions=INSTRUCTIONS,
        model=model,
        tools=[get_weather, calculator],
    )


async def run(agent: Agent, goal: str = GOAL, *, offline: bool = True) -> RunResult:
    """Run the agent loop. Tracing to the OpenAI dashboard is switched off for offline runs."""
    return await Runner.run(agent, goal, max_turns=6, run_config=RunConfig(tracing_disabled=offline))


def trace(result: RunResult) -> list[str]:
    """A readable list of what happened during the run."""
    lines = []
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            lines.append(f"tool call:   {item.raw_item.name}({item.raw_item.arguments})")
        elif isinstance(item, ToolCallOutputItem):
            lines.append(f"tool result: {item.output}")
        elif isinstance(item, MessageOutputItem):
            lines.append(f"message:     {ItemHelpers.text_message_output(item)}")
    return lines


def main() -> None:
    offline = (os.getenv("LLM_PROVIDER") or "mock").lower() == "mock"
    if offline:
        model: Model | str = scripted_model()
    elif (os.getenv("LLM_PROVIDER") or "").lower() == "openai" and os.getenv("OPENAI_MODEL"):
        model = os.environ["OPENAI_MODEL"]  # a model name: the SDK calls the Responses API
    else:
        sys.exit("Use LLM_PROVIDER=mock, or LLM_PROVIDER=openai with OPENAI_MODEL and OPENAI_API_KEY set.")

    result = asyncio.run(run(build_agent(model), offline=offline))
    print(f"Goal: {GOAL}\n")
    print("\n".join(trace(result)))
    print(f"\nAnswer: {result.final_output}")


if __name__ == "__main__":
    main()
