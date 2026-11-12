"""Project 1 solution: a weather + calculator agent.

Two tools (get_weather and a safe calculator) and an agent loop with a step
limit and error handling. Offline by default: fake weather data and MockLLM.

    python solution/main.py                          # from the project folder
    python 18-project-1-weather-calculator/solution/main.py   # from examples/
    python solution/main.py "Weather in Rome?"        # your own question (needs a real model)

Optional real weather: set WEATHER_SOURCE=open-meteo to call the free
Open-Meteo API (no key needed; check their terms of use).

Read alongside docs/18-projects/18.1-project-1-weather-and-calculator-agent.md.
"""

from __future__ import annotations

import ast
import json
import math
import operator
import os
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

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
    """Current weather for one city as JSON. Uses fake data unless WEATHER_SOURCE=open-meteo."""
    city = city.strip()
    if not city:
        raise ValueError("city must not be empty")
    if os.getenv("WEATHER_SOURCE", "fake").lower() == "open-meteo":
        return fetch_open_meteo(city)
    data = FAKE_WEATHER.get(city.lower())
    if data is None:
        known = ", ".join(c.title() for c in FAKE_WEATHER)
        raise LookupError(f"Unknown city {city!r}. Known cities: {known}.")
    return json.dumps({"city": city.title(), **data, "source": "fake"})


def _get_json(url: str, opener: Callable[..., Any] = urllib.request.urlopen) -> Any:
    with opener(url, timeout=10) as resp:  # always set a timeout on network calls
        return json.loads(resp.read().decode("utf-8"))


def fetch_open_meteo(city: str, opener: Callable[..., Any] = urllib.request.urlopen) -> str:
    """Real weather from Open-Meteo: geocode the city name, then fetch current conditions."""
    q = urllib.parse.urlencode({"name": city, "count": 1})
    geo = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{q}", opener)
    if not geo.get("results"):
        raise LookupError(f"Unknown city {city!r}.")
    place = geo["results"][0]
    q = urllib.parse.urlencode(
        {"latitude": place["latitude"], "longitude": place["longitude"], "current": "temperature_2m,wind_speed_10m"}
    )
    now = _get_json(f"https://api.open-meteo.com/v1/forecast?{q}", opener)["current"]
    return json.dumps(
        {
            "city": place["name"],
            "temp_c": now["temperature_2m"],
            "wind_kph": now["wind_speed_10m"],
            "source": "open-meteo",
        }
    )


# --------------------------------------------------------------------------- tool 2: a safe calculator

_BIN_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
MAX_EXPONENT = 100  # stops '9 ** 9 ** 9' from freezing the process


def calculator(expression: str) -> str:
    """Evaluate arithmetic: numbers, + - * / % ** and brackets. Never uses eval()."""
    if len(expression) > 200:
        raise ValueError("expression too long (max 200 characters)")

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = ev(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
                raise ValueError(f"exponent too large (max {MAX_EXPONENT})")
            return _BIN_OPS[type(node.op)](left, right)
        raise ValueError("only numbers, + - * / % ** and brackets are allowed")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"not a valid expression: {expression!r}") from exc
    result = ev(tree.body)
    if isinstance(result, float):
        if not math.isfinite(result):
            raise ValueError("result is not a finite number")
        result = round(result, 6)
        if result.is_integer():
            result = int(result)
    return str(result)


# --------------------------------------------------------------------------- tool descriptions (what the model sees)

TOOL_SPECS: list[ToolSpec] = [
    {
        "name": "get_weather",
        "description": (
            "Get the current weather for ONE city: temperature in °C, a short condition and wind in km/h. "
            "Call it once per city. Returns JSON, or an error if the city is unknown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name in English, e.g. 'Paris'."}},
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": (
            "Evaluate an arithmetic expression exactly. Supports numbers, + - * / % ** and brackets, "
            "e.g. '(14 + 19) / 2' or '14 * 9 / 5 + 32'. Use it for ALL arithmetic instead of doing maths yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "The expression to evaluate."}},
            "required": ["expression"],
        },
    },
]
TOOLS: dict[str, Callable[..., str]] = {"get_weather": get_weather, "calculator": calculator}

SYSTEM_PROMPT = (
    "You are a friendly weather assistant. "
    "Use get_weather for every temperature you mention; never guess the weather. "
    "Use calculator for every calculation, including unit conversions (°F = °C * 9 / 5 + 32). "
    "If a tool returns an error, explain the problem to the user in plain words. "
    "Answer in one to three short sentences."
)


# --------------------------------------------------------------------------- the agent loop


@dataclass
class AgentResult:
    """What one run produced: the answer, how many model calls it took, and a readable trace."""

    answer: str
    steps: int
    trace: list[str] = field(default_factory=list)
    stopped_by_limit: bool = False


def run_tool(name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
    """Run one tool. Returns (output, is_error). Never raises: errors go back to the model as text."""
    fn = TOOLS.get(name)
    if fn is None:
        return f"Error: unknown tool {name!r}. Available tools: {', '.join(TOOLS)}.", True
    try:
        return fn(**arguments), False
    except TypeError as exc:  # wrong or missing arguments
        return f"Error: bad arguments for {name}: {exc}", True
    except (ValueError, LookupError, ZeroDivisionError, OSError) as exc:
        return f"Error: {exc}", True


def run_agent(llm: LLM, question: str, *, max_steps: int = 5) -> AgentResult:
    """Think, act, observe until the model answers or max_steps model calls have been made."""
    messages: list[Message] = [user(question)]
    trace: list[str] = []
    for step in range(1, max_steps + 1):
        reply = llm.chat(messages, system=SYSTEM_PROMPT, tools=TOOL_SPECS)
        messages.append(reply.to_message())

        if not reply.tool_calls:  # the model chose to answer
            if reply.stop_reason == "max_tokens":
                trace.append(f"step {step}: answer was cut off (max_tokens)")
            trace.append(f"step {step}: answer")
            return AgentResult(reply.text, step, trace)

        for call in reply.tool_calls:  # run every requested tool; all results go back together
            if call.error:  # the provider sent arguments that were not valid JSON
                output, is_error = f"Error: {call.error}", True
            else:
                output, is_error = run_tool(call.name, call.arguments)
            trace.append(f"step {step}: {call.name}({json.dumps(call.arguments)}) -> {output}")
            messages.append(tool_result(call.id, output, is_error=is_error))

    trace.append(f"stopped: reached the limit of {max_steps} steps")
    return AgentResult(
        "Sorry, I could not finish that within my step limit. Try a simpler question.",
        max_steps,
        trace,
        stopped_by_limit=True,
    )


# --------------------------------------------------------------------------- demo

DEMO_QUESTION = "What's the average temperature in Paris and Rome right now, in °F?"
DEMO_SCRIPT = [
    MockLLM.tool_calls([("get_weather", {"city": "Paris"}), ("get_weather", {"city": "Rome"})]),
    MockLLM.tool_call("calculator", {"expression": "(14 + 19) / 2 * 9 / 5 + 32"}),
    "It's 14°C and cloudy in Paris and 19°C and sunny in Rome. The average is 16.5°C, which is 61.7°F.",
]
ERROR_QUESTION = "What's the weather in Atlantis?"
ERROR_SCRIPT = [
    MockLLM.tool_call("get_weather", {"city": "Atlantis"}),
    "Sorry, I don't have weather for Atlantis. I can check Paris, Rome, London, Tokyo, Cairo or New York.",
]


def show(llm: LLM, question: str) -> None:
    print(f"Question: {question}")
    result = run_agent(llm, question)
    print("\n".join("  " + line for line in result.trace))
    print(f"Answer: {result.answer}\n")


def main() -> None:
    if len(sys.argv) > 1:  # your own question: best with LLM_PROVIDER=anthropic or openai
        show(get_llm(), " ".join(sys.argv[1:]))
        return
    show(get_llm(mock_responses=DEMO_SCRIPT), DEMO_QUESTION)
    show(get_llm(mock_responses=ERROR_SCRIPT), ERROR_QUESTION)


if __name__ == "__main__":
    main()
