"""The Paris-vs-Rome weather agent from 1.5, rebuilt with Pydantic AI.

    python main.py                      # from this folder (offline, FunctionModel)
    python 11-pydantic-ai/main.py       # from examples/

    LLM_PROVIDER=anthropic python main.py                       # Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py     # OpenAI (needs OPENAI_API_KEY)

Offline, the agent runs with Pydantic AI's own test double, `FunctionModel`: a
plain Python function plays the model, and everything else (tool schemas,
argument validation, the loop) is the real framework. Needs
`pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.8-pydantic-ai.md.
"""

from __future__ import annotations

import ast
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
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # hide the start-up banner so the output stays short

from pydantic_ai import (  # noqa: E402
    Agent,
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UsageLimits,
)
from pydantic_ai.models import Model  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}

INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
ANSWER = "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C."

# The agent: instructions + tools. The model is chosen when you run it.
agent = Agent(instructions=INSTRUCTIONS)

_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


@agent.tool_plain  # "plain": the tool does not need the run context
def get_weather(city: str) -> str:
    """Get the current temperature in °C for one city.

    Args:
        city: City name, e.g. 'Paris'.
    """
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


@agent.tool_plain
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'.

    Args:
        expression: The expression to evaluate.
    """

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


# --------------------------------------------------------------------------- the offline "model"


def scripted_reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Play the model: decide the next reply from how many replies have been given so far."""
    replies_so_far = sum(isinstance(m, ModelResponse) for m in messages)
    if replies_so_far == 0:  # step 1: ask for both cities at once
        return ModelResponse(
            parts=[ToolCallPart("get_weather", {"city": "Paris"}), ToolCallPart("get_weather", {"city": "Rome"})]
        )
    if replies_so_far == 1:  # step 2: do the arithmetic with a tool, not in its head
        return ModelResponse(parts=[ToolCallPart("calculator", {"expression": "19 - 14"})])
    return ModelResponse(parts=[TextPart(ANSWER)])  # step 3: answer


def choose_model() -> Model | str:
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        return "anthropic:" + (os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5")
    if provider == "openai":
        return "openai:" + os.environ["OPENAI_MODEL"]
    return FunctionModel(scripted_reply)


def trace(messages: list[ModelMessage]) -> list[str]:
    """A readable list of the tool calls and results in a run."""
    lines = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                lines.append(f"tool call:   {part.tool_name}({part.args_as_json_str()})")
            elif isinstance(part, ToolReturnPart):
                lines.append(f"tool result: {part.content}")
    return lines


def main() -> None:
    # UsageLimits is the loop's safety net: at most 6 model requests per run.
    result = agent.run_sync(GOAL, model=choose_model(), usage_limits=UsageLimits(request_limit=6))
    print(f"Goal: {GOAL}\n")
    print("\n".join(trace(result.all_messages())))
    print(f"\nAnswer: {result.output}")
    print(f"Model requests: {result.usage.requests}")


if __name__ == "__main__":
    main()
