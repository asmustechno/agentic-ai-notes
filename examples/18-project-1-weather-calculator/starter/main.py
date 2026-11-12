"""Project 1 starter: build a weather + calculator agent.

Fill in every `# TODO`. The file runs as it is and tells you what is missing:

    python starter/main.py

Check your work with the same tests the solution passes:

    PROJECT_TARGET=starter pytest 18-project-1-weather-calculator        # macOS/Linux, from examples/
    $env:PROJECT_TARGET="starter"; pytest 18-project-1-weather-calculator  # Windows PowerShell

Guide: docs/18-projects/18.1-project-1-weather-and-calculator-agent.md
"""

from __future__ import annotations

import ast
import json  # noqa: F401  (you will need it)
import operator
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402,F401

# --------------------------------------------------------------------------- tool 1: get_weather

FAKE_WEATHER: dict[str, dict[str, Any]] = {
    "paris": {"temp_c": 14, "condition": "cloudy", "wind_kph": 12},
    "rome": {"temp_c": 19, "condition": "sunny", "wind_kph": 8},
    "london": {"temp_c": 11, "condition": "light rain", "wind_kph": 20},
    "tokyo": {"temp_c": 18, "condition": "clear", "wind_kph": 6},
    "cairo": {"temp_c": 27, "condition": "sunny", "wind_kph": 14},
    "new york": {"temp_c": 9, "condition": "windy", "wind_kph": 31},
}


def get_weather(city: str) -> str:
    """Return the weather for one city as a JSON string.

    Example: get_weather("paris") -> '{"city": "Paris", "temp_c": 14, "condition": "cloudy", ...}'
    Raise LookupError for an unknown city (the message should list the known cities)
    and ValueError for an empty name.
    """
    # TODO (milestone 1): look the city up in FAKE_WEATHER, case-insensitively, and return json.dumps(...)
    raise NotImplementedError("get_weather is not written yet (milestone 1)")


# --------------------------------------------------------------------------- tool 2: a safe calculator

_BIN_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
MAX_EXPONENT = 100


def calculator(expression: str) -> str:
    """Evaluate arithmetic safely and return the result as a string, e.g. '(14 + 19) / 2' -> '16.5'.

    Rules: numbers, + - * / % ** and brackets only. Never call eval(). Raise ValueError for
    anything else (names, function calls, huge exponents, expressions over 200 characters).
    Whole-number results print without '.0'.
    """
    # TODO (milestone 2): ast.parse(expression, mode="eval"), then walk the tree yourself:
    #   ast.Constant (int/float) -> its value; ast.UnaryOp (- or +); ast.BinOp with an op in _BIN_OPS.
    raise NotImplementedError("calculator is not written yet (milestone 2)")


# --------------------------------------------------------------------------- tool descriptions (what the model sees)

TOOL_SPECS: list[ToolSpec] = [
    {
        "name": "get_weather",
        # TODO (milestone 3): a description that tells the model what it returns and when to call it.
        "description": "TODO",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name in English, e.g. 'Paris'."}},
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        # TODO (milestone 3): say which operators work and give an example expression.
        "description": "TODO",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "The expression to evaluate."}},
            "required": ["expression"],
        },
    },
]
TOOLS: dict[str, Callable[..., str]] = {"get_weather": get_weather, "calculator": calculator}

# TODO (milestone 3): tell the model to use get_weather for every temperature and calculator for all maths.
SYSTEM_PROMPT = "You are a friendly weather assistant."


# --------------------------------------------------------------------------- the agent loop


@dataclass
class AgentResult:
    """What one run produced: the answer, how many model calls it took, and a readable trace."""

    answer: str
    steps: int
    trace: list[str] = field(default_factory=list)
    stopped_by_limit: bool = False


def run_tool(name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
    """Run one tool and return (output, is_error). Must never raise.

    Unknown tool, wrong arguments (TypeError) and tool errors (ValueError, LookupError, ...)
    all become ("Error: ...", True) so the model can read the problem and recover.
    """
    # TODO (milestone 4)
    raise NotImplementedError("run_tool is not written yet (milestone 4)")


def run_agent(llm: LLM, question: str, *, max_steps: int = 5) -> AgentResult:
    """The agent loop: call the model, run the tools it asks for, repeat.

    1. messages = [user(question)]
    2. reply = llm.chat(messages, system=SYSTEM_PROMPT, tools=TOOL_SPECS); append reply.to_message()
    3. No tool calls? Return AgentResult(reply.text, step, trace).
    4. Otherwise run each call with run_tool and append tool_result(call.id, output, is_error=...).
    5. After max_steps model calls, stop with stopped_by_limit=True.
    Add a line to `trace` for each tool call ("step 1: get_weather({...}) -> ...") and for the answer.
    """
    # TODO (milestone 5)
    raise NotImplementedError("run_agent is not written yet (milestone 5)")


# --------------------------------------------------------------------------- demo (already done)

DEMO_QUESTION = "What's the average temperature in Paris and Rome right now, in °F?"
DEMO_SCRIPT = [
    MockLLM.tool_calls([("get_weather", {"city": "Paris"}), ("get_weather", {"city": "Rome"})]),
    MockLLM.tool_call("calculator", {"expression": "(14 + 19) / 2 * 9 / 5 + 32"}),
    "It's 14°C and cloudy in Paris and 19°C and sunny in Rome. The average is 16.5°C, which is 61.7°F.",
]


def main() -> None:
    print(f"Question: {DEMO_QUESTION}")
    try:
        result = run_agent(get_llm(mock_responses=DEMO_SCRIPT), DEMO_QUESTION)
    except NotImplementedError as exc:
        print(f"Not finished yet: {exc}. Open starter/main.py and look for '# TODO'.")
        return
    print("\n".join("  " + line for line in result.trace))
    print(f"Answer: {result.answer}")


if __name__ == "__main__":
    main()
