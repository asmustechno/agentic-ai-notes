"""An agent loop that gets its tools from an MCP server.

The agent knows nothing about notes. It connects to the notes server from 4.4,
lists its tools, converts them to the wrapper's neutral ToolSpec format, and
forwards every tool call the model makes to the server.

    python main.py            # launches ../04-mcp-server/notes_server.py over stdio
    python main.py --inproc   # connects in-process instead (what the tests use)

Read alongside docs/04-model-context-protocol/04.5-connect-mcp-to-an-agent.md.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from mcp import Client, StdioServerParameters  # noqa: E402
from mcp.types import CallToolResult, Tool  # noqa: E402

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

NOTES_SERVER = Path(__file__).resolve().parent.parent / "04-mcp-server" / "notes_server.py"

# --------------------------------------------------------------------------- MCP -> neutral format


def to_tool_spec(tool: Tool, prefix: str = "") -> ToolSpec:
    """Convert an MCP tool definition into the wrapper's neutral {name, description, input_schema}."""
    return {
        "name": prefix + tool.name,
        "description": tool.description or "",
        "input_schema": tool.input_schema,  # MCP already uses JSON Schema, so this copies straight over
    }


def to_text(result: CallToolResult) -> str:
    """Flatten an MCP tool result into the text we hand back to the model."""
    parts: list[str] = []
    for block in result.content:
        if block.type == "text":
            parts.append(block.text)
        else:  # images, audio, resource links...: describe them rather than drop them silently
            parts.append(f"[{block.type} content omitted]")
    if not parts and result.structured_content is not None:
        parts.append(json.dumps(result.structured_content))
    return "\n".join(parts)


def fingerprint(tool: Tool) -> str:
    """A hash of everything the model reads about a tool. If it changes, the tool changed."""
    payload = json.dumps([tool.name, tool.description, tool.input_schema], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- the agent


@dataclass
class MCPAgent:
    """A plain agent loop whose tools live on an MCP server."""

    model: LLM
    instructions: str
    allowed_tools: set[str] | None = None  # least privilege: expose only these server tools (None = all)
    pinned: dict[str, str] | None = None  # name -> fingerprint approved earlier; changed tools are dropped
    max_steps: int = 6
    log: list[str] = field(default_factory=list)

    async def run(self, goal: str, client: Client) -> str:
        # 1. Discover: ask the server which tools it has, keep the allowed ones.
        listed = (await client.list_tools()).tools
        tools = [t for t in listed if self.allowed_tools is None or t.name in self.allowed_tools]
        if self.pinned is not None:  # defend against "rug pulls": definitions changed after approval
            changed = [t.name for t in tools if self.pinned.get(t.name) != fingerprint(t)]
            if changed:
                self.log.append(f"refusing tools whose definition changed since approval: {changed}")
            tools = [t for t in tools if t.name not in changed]
        specs = [to_tool_spec(t) for t in tools]
        self.log.append(f"tools/list -> {[t.name for t in listed]}; exposing {[s['name'] for s in specs]}")

        messages: list[Message] = [user(goal)]
        for step in range(1, self.max_steps + 1):
            # 2. Think: the model sees the MCP tools as if they were ordinary tools.
            reply: LLMResponse = self.model.chat(messages, system=self.instructions, tools=specs)
            messages.append(reply.to_message())
            if not reply.tool_calls:
                self.log.append(f"step {step}: answer")
                return reply.text

            # 3. Act: forward each call to the MCP server, then return the results together.
            for call in reply.tool_calls:
                if call.name not in {s["name"] for s in specs}:
                    text, is_error = f"Tool {call.name!r} is not available.", True
                else:
                    result = await client.call_tool(call.name, call.arguments)
                    text, is_error = to_text(result), bool(result.is_error)
                self.log.append(f"step {step}: tools/call {call.name}({call.arguments}) -> {text!r}"
                                + ("  [is_error]" if is_error else ""))
                messages.append(tool_result(call.id, text, is_error=is_error))  # 4. Observe
        return "I could not finish within the step limit."


INSTRUCTIONS = (
    "You are a personal assistant with access to the user's notes. "
    "Search the notes before answering questions about plans. Save new facts the user asks you to remember. "
    "Answer in one or two sentences."
)
GOAL = "Remember that my dentist appointment is on Friday at 15:00. Then tell me everything I have on Friday."


def answer_from_last_result(messages: list[Message]) -> str:
    """Scripted final reply that reads the search result, like a real model would."""
    lines = [line for line in messages[-1]["content"].splitlines() if ": " in line]  # "title: text" lines
    if not lines:
        return "Saved. I found nothing else for Friday."
    hits = [line.split(": ", 1)[1].rstrip(".") for line in lines]
    return "Saved. On Friday you have: " + "; ".join(hits) + "."


SCRIPT = [
    MockLLM.tool_call("add_note", {"title": "dentist", "text": "Dentist appointment on Friday at 15:00."}),
    MockLLM.tool_call("search_notes", {"query": "friday"}),
    answer_from_last_result,
]


def load_notes_server() -> Any:
    """Import the 4.4 server module from its file (examples are folders, not packages)."""
    spec = importlib.util.spec_from_file_location("notes_server_for_agent", NOTES_SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def run(model: LLM, target: object, *, allowed_tools: set[str] | None = None) -> tuple[str, MCPAgent]:
    agent = MCPAgent(model=model, instructions=INSTRUCTIONS, allowed_tools=allowed_tools)
    async with Client(target) as client:
        answer = await agent.run(GOAL, client)
    return answer, agent


def main() -> None:
    logging.getLogger("mcp").setLevel(logging.CRITICAL)
    if "--inproc" in sys.argv:
        target: object = load_notes_server().build_server()
    else:
        target = StdioServerParameters(command=sys.executable, args=[str(NOTES_SERVER)])
    print(f"Goal: {GOAL}\n")
    answer, agent = asyncio.run(run(get_llm(mock_responses=SCRIPT), target))
    print("\n".join(agent.log))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
