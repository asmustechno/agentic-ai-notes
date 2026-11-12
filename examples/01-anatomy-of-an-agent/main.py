"""The five parts of an agent, each clearly labelled.

    ① model  ② instructions  ③ tools  ④ memory  ⑤ loop

    python main.py                            # from this folder
    python 01-anatomy-of-an-agent/main.py     # from examples/

Read alongside docs/01-foundations/01.5-anatomy-of-an-agent.md.
Chapter 2 rebuilds this loop step by step and makes it robust.
"""

from __future__ import annotations

import ast
import json
import operator
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- ③ tools (plain Python functions)

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}


def get_weather(city: str) -> str:
    """Current temperature for a city, in °C (fake data for the demo)."""
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculator(expression: str) -> str:
    """Evaluate simple arithmetic like '19 - 14'. Safe: no eval(), only + - * / and numbers."""

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


WEATHER_SPEC: ToolSpec = {
    "name": "get_weather",
    "description": "Get the current temperature in °C for one city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name, e.g. 'Paris'."}},
        "required": ["city"],
    },
}
CALCULATOR_SPEC: ToolSpec = {
    "name": "calculator",
    "description": "Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'.",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
}


# --------------------------------------------------------------------------- the agent


@dataclass
class Agent:
    model: LLM  # ① MODEL: reads, reasons and decides the next step
    instructions: str  # ② INSTRUCTIONS: role, goal and rules (the system prompt)
    tools: dict[str, tuple[Callable[..., str], ToolSpec]]  # ③ TOOLS: name -> (function, description for the model)
    facts: list[str] = field(default_factory=list)  # ④ MEMORY (long-term): facts kept between runs
    max_steps: int = 6  # ⑤ LOOP: a hard limit so it always stops
    log: list[str] = field(default_factory=list)

    def run(self, goal: str) -> str:
        messages: list[Message] = [user(goal)]  # ④ MEMORY (short-term): this conversation
        system = self.instructions
        if self.facts:
            system += "\n\nThings you remember about the user:\n" + "\n".join(f"- {f}" for f in self.facts)
        specs = [spec for _, spec in self.tools.values()]

        for step in range(1, self.max_steps + 1):  # ⑤ LOOP
            reply = self.model.chat(messages, system=system, tools=specs)  # ① think
            messages.append(reply.to_message())
            if not reply.tool_calls:  # the model chose to stop
                self.log.append(f"step {step}: answer")
                return reply.text
            for call in reply.tool_calls:  # ③ act
                fn, _ = self.tools[call.name]
                result = fn(**call.arguments)
                self.log.append(f"step {step}: {call.name}({call.arguments}) -> {result}")
                messages.append(tool_result(call.id, result))  # ④ observe: remember the result
        return "I could not finish within the step limit."


INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
SCRIPT = [
    MockLLM.tool_calls([("get_weather", {"city": "Paris"}), ("get_weather", {"city": "Rome"})]),
    MockLLM.tool_call("calculator", {"expression": "19 - 14"}),
    "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.",
]


def build_agent(llm: LLM) -> Agent:
    return Agent(
        model=llm,
        instructions=INSTRUCTIONS,
        tools={"get_weather": (get_weather, WEATHER_SPEC), "calculator": (calculator, CALCULATOR_SPEC)},
        facts=["Prefers temperatures in Celsius."],
    )


def main() -> None:
    agent = build_agent(get_llm(mock_responses=SCRIPT))
    print(f"Goal: {GOAL}\n")
    answer = agent.run(GOAL)
    print("\n".join(agent.log))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
