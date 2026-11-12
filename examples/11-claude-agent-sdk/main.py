"""The Paris-vs-Rome weather agent from 1.5, rebuilt with the Claude Agent SDK.

    python main.py                         # from this folder
    python 11-claude-agent-sdk/main.py     # from examples/

The Agent SDK runs the Claude Code agent loop (the SDK ships a bundled Claude
Code binary and talks to it). There is no offline model, so:

  * with ANTHROPIC_API_KEY set, `python main.py` runs the real agent;
  * without it, the script says so and replays the run locally: it calls the
    same tool handlers in the order Claude would, so you can see the shapes.

Our tools run in-process as an SDK MCP server. `tools=[]` removes Claude Code's
built-in tools (Bash, Read, Edit, ...) so this agent can only use ours.
Needs `pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.6-claude-agent-sdk.md.
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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolAnnotations,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

# --------------------------------------------------------------------------- tools: async handlers that return MCP content


def _text(text: str, *, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["is_error"] = True
    return result


@tool(
    "get_weather",
    "Get the current temperature in °C for one city.",
    {"city": str},
    annotations=ToolAnnotations(readOnlyHint=True),  # read-only tools may run in parallel
)
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    city = args["city"]
    temp = FAKE_WEATHER.get(city.lower())
    if temp is None:
        return _text(f"Unknown city: {city}", is_error=True)
    return _text(json.dumps({"city": city, "temp_c": temp}))


@tool(
    "calculator",
    "Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'.",
    {"expression": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def calculator(args: dict[str, Any]) -> dict[str, Any]:
    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        raise ValueError("only numbers and + - * / are allowed")

    try:
        return _text(str(ev(ast.parse(args["expression"], mode="eval").body)))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return _text(f"Error: {exc}", is_error=True)


# --------------------------------------------------------------------------- the agent

INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
SERVER = "travel"  # MCP tool names become mcp__<server>__<tool>
TOOL_NAMES = [f"mcp__{SERVER}__get_weather", f"mcp__{SERVER}__calculator"]


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(name=SERVER, version="1.0.0", tools=[get_weather, calculator])
    return ClaudeAgentOptions(
        system_prompt=INSTRUCTIONS,  # a plain string is the whole system prompt (Claude Code's preset is opt-in)
        mcp_servers={SERVER: server},
        tools=[],  # no built-in tools: no Bash, no file access
        allowed_tools=TOOL_NAMES,  # pre-approve our two tools, so no permission prompt
        setting_sources=[],  # ignore any CLAUDE.md or settings on this machine
        max_turns=6,  # the loop's safety net
        model=(os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"),
    )


async def run(goal: str = GOAL) -> tuple[str, list[str]]:
    """Run the real agent. Needs ANTHROPIC_API_KEY. Returns the answer and a trace."""
    lines: list[str] = []
    answer = ""
    async for message in query(prompt=goal, options=build_options()):
        if isinstance(message, AssistantMessage):
            lines += [f"tool call:   {b.name}({json.dumps(b.input)})" for b in message.content if isinstance(b, ToolUseBlock)]
        elif isinstance(message, ResultMessage):
            answer = message.result or ""
            lines.append(f"result:      {message.subtype}, {message.num_turns} turns, ${message.total_cost_usd or 0:.4f}")
    return answer, lines


async def replay_locally() -> list[str]:
    """No API key: call our handlers in the order Claude would, to show what it would see."""
    lines = []
    for handler, args in [(get_weather, {"city": "Paris"}), (get_weather, {"city": "Rome"}), (calculator, {"expression": "19 - 14"})]:
        result = await handler.handler(args)
        lines.append(f"tool call:   mcp__{SERVER}__{handler.name}({json.dumps(args)}) -> {result['content'][0]['text']}")
    return lines


def main() -> None:
    print(f"Goal: {GOAL}\n")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set, so this script does not start a real Claude Code session.")
        print("Replaying the expected tool calls locally instead:\n")
        print("\n".join(asyncio.run(replay_locally())))
        return
    answer, lines = asyncio.run(run())
    print("\n".join(lines))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
