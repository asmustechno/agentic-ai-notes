"""The Paris-vs-Rome weather agent from 1.5, rebuilt with a LlamaIndex FunctionAgent.

    python main.py                   # from this folder (offline, MockFunctionCallingLLM)
    python 11-llamaindex/main.py     # from examples/

    LLM_PROVIDER=anthropic python main.py                     # Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # OpenAI (needs OPENAI_API_KEY)

Offline, the agent uses LlamaIndex's own `MockFunctionCallingLLM` with a
response generator that scripts the model's replies; the FunctionAgent
workflow, tool schemas and tool execution are real. Needs
`pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.7-llamaindex-agents.md.
"""

from __future__ import annotations

import ast
import asyncio
import json
import operator
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass

from llama_index.core.agent.workflow import FunctionAgent, ToolCall, ToolCallResult  # noqa: E402
from llama_index.core.base.llms.types import ToolCallBlock  # noqa: E402
from llama_index.core.llms import LLM, ChatMessage, MessageRole, MockFunctionCallingLLM  # noqa: E402

# --------------------------------------------------------------------------- tools: plain functions

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

# --------------------------------------------------------------------------- the model


def _call(name: str, args: dict[str, Any], call_id: str) -> ToolCallBlock:
    return ToolCallBlock(tool_call_id=call_id, tool_name=name, tool_kwargs=args)


def scripted_reply(messages: Sequence[ChatMessage], **kwargs: Any) -> ChatMessage:
    """Play the model: pick the next reply from how many tool results it has seen."""
    results_seen = sum(m.role == MessageRole.TOOL for m in messages)
    if results_seen == 0:
        blocks = [_call("get_weather", {"city": "Paris"}, "call_1"), _call("get_weather", {"city": "Rome"}, "call_2")]
        return ChatMessage(role=MessageRole.ASSISTANT, blocks=blocks)
    if results_seen == 2:
        return ChatMessage(role=MessageRole.ASSISTANT, blocks=[_call("calculator", {"expression": "19 - 14"}, "call_3")])
    return ChatMessage(role=MessageRole.ASSISTANT, content=ANSWER)


def choose_llm() -> LLM:
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        from llama_index.llms.anthropic import Anthropic

        return Anthropic(model=(os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"), max_tokens=4096)
    if provider == "openai":
        from llama_index.llms.openai import OpenAI

        return OpenAI(model=os.environ["OPENAI_MODEL"])
    return MockFunctionCallingLLM(response_generator=scripted_reply)


# --------------------------------------------------------------------------- the agent


def build_agent(llm: LLM) -> FunctionAgent:
    # Plain functions become tools: LlamaIndex reads the name, type hints and docstring.
    return FunctionAgent(tools=[get_weather, calculator], llm=llm, system_prompt=INSTRUCTIONS)


async def run(agent: FunctionAgent, goal: str = GOAL, max_iterations: int = 6) -> tuple[str, list[str]]:
    """Run the agent and collect a trace from the workflow's event stream."""
    handler = agent.run(user_msg=goal, max_iterations=max_iterations)
    lines = []
    async for event in handler.stream_events():
        if isinstance(event, ToolCallResult):
            lines.append(f"tool result: {event.tool_output.content}")
        elif isinstance(event, ToolCall):
            lines.append(f"tool call:   {event.tool_name}({json.dumps(event.tool_kwargs)})")
    response = await handler
    return str(response), lines


def main() -> None:
    answer, lines = asyncio.run(run(build_agent(choose_llm())))
    print(f"Goal: {GOAL}\n")
    print("\n".join(lines))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
