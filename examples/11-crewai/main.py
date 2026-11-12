"""The Paris-vs-Rome weather agent from 1.5, rebuilt as a one-agent CrewAI crew.

    python main.py                # from this folder (offline, scripted LLM)
    python 11-crewai/main.py      # from examples/

    LLM_PROVIDER=anthropic python main.py                     # Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # OpenAI (needs OPENAI_API_KEY)

CrewAI has no built-in fake model, so offline we subclass `BaseLLM` (CrewAI's
documented custom-LLM extension point). Its `call()` returns scripted
OpenAI-style tool calls, which CrewAI's agent executor then runs natively;
the Agent, Task, Crew and tool execution are real. Needs
`pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.3-crewai.md.
"""

from __future__ import annotations

import ast
import json
import operator
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")  # no anonymous usage data from this demo
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")  # and no trace upload prompt

from crewai import LLM, Agent, BaseLLM, Crew, CrewOutput, Process, Task  # noqa: E402
from crewai.tools import tool  # noqa: E402

# --------------------------------------------------------------------------- tools

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
TOOL_LOG: list[str] = []  # what the tools were asked to do, for the printed trace


@tool("get_weather")
def get_weather(city: str) -> str:
    """Get the current temperature in °C for one city, e.g. 'Paris'."""
    temp = FAKE_WEATHER.get(city.lower())
    result = json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"
    TOOL_LOG.append(f"get_weather({city!r}) -> {result}")
    return result


@tool("calculator")
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
        result = str(ev(ast.parse(expression, mode="eval").body))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        result = f"Error: {exc}"
    TOOL_LOG.append(f"calculator({expression!r}) -> {result}")
    return result


GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
ANSWER = "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C."

# --------------------------------------------------------------------------- the offline "model"


def _tool_call(call_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """One tool call in the OpenAI format that CrewAI's native tool calling understands."""
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def scripted_reply(messages: list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    """Play the model: pick the next reply from how many tool results it has seen."""
    results_seen = sum(m.get("role") == "tool" for m in messages)
    if results_seen == 0:
        return [_tool_call("call_1", "get_weather", {"city": "Paris"}), _tool_call("call_2", "get_weather", {"city": "Rome"})]
    if results_seen == 2:
        return [_tool_call("call_3", "calculator", {"expression": "19 - 14"})]
    return ANSWER


class ScriptedLLM(BaseLLM):
    """A custom CrewAI LLM whose replies come from a Python function. It records every call."""

    reply: Callable[[list[dict[str, Any]]], Any] = scripted_reply
    calls: list[dict[str, Any]] = []

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):  # type: ignore[no-untyped-def, override]
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.reply(messages)

    def supports_function_calling(self) -> bool:
        return True  # so CrewAI sends tool schemas and expects tool calls back

    def get_input_tokens_count(self, messages, tools=None, response_model=None) -> int:  # type: ignore[no-untyped-def, override]
        """A rough count (4 characters per token), without the base class's warning."""
        text = messages if isinstance(messages, str) else " ".join(str(m.get("content", "")) for m in messages)
        return len(text) // 4 + 1


def choose_llm() -> BaseLLM:
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        return LLM(model="anthropic/" + (os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"))
    if provider == "openai":
        return LLM(model="openai/" + os.environ["OPENAI_MODEL"])
    return ScriptedLLM(model="scripted", calls=[])


# --------------------------------------------------------------------------- the crew


def build_crew(llm: BaseLLM) -> Crew:
    # An agent is a role with a goal and a backstory. Those three become its instructions.
    forecaster = Agent(
        role="Travel weather assistant",
        goal="Compare current temperatures between cities using real data, never guesses.",
        backstory="You are concise. You always use get_weather for temperatures and calculator for arithmetic.",
        tools=[get_weather, calculator],
        llm=llm,
        max_iter=6,  # the loop's safety net
        verbose=False,
    )
    # A task is a unit of work with a clear expected output, assigned to an agent.
    compare = Task(
        description=GOAL,
        expected_output="One or two sentences naming the warmer city and the difference in °C.",
        agent=forecaster,
    )
    return Crew(agents=[forecaster], tasks=[compare], process=Process.sequential, verbose=False)


def main() -> None:
    TOOL_LOG.clear()
    result: CrewOutput = build_crew(choose_llm()).kickoff()
    print(f"Goal: {GOAL}\n")
    print("\n".join(f"tool: {line}" for line in TOOL_LOG))
    print(f"\nAnswer: {result.raw}")


if __name__ == "__main__":
    main()
