"""Connect an MCP client to the notes server and try everything it offers.

    python main.py            # in-process connection (fast, used by the tests)
    python main.py --stdio    # launch notes_server.py as a subprocess, like a real host does

No model is involved here: this is the client side of MCP on its own. Page 4.5
adds a model and an agent loop on top.

Read alongside docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `notes_server` importable

from mcp import Client, StdioServerParameters  # noqa: E402
from mcp.types import CallToolResult  # noqa: E402

from notes_server import build_server  # noqa: E402

SERVER_FILE = Path(__file__).resolve().parent / "notes_server.py"


def result_text(result: CallToolResult) -> str:
    """Join the text blocks of a tool result into one string."""
    return "\n".join(block.text for block in result.content if block.type == "text")


async def tour(target: object) -> list[str]:
    """Discover and use every primitive on the server. Returns the printed lines."""
    lines: list[str] = []
    async with Client(target) as client:
        info = client.server_info
        lines.append(f"Connected to {info.name if info else '?'} {info.version if info else ''} "
                     f"(protocol {client.protocol_version})")

        lines.append("\nTOOLS (the model decides when to call these)")
        for tool in (await client.list_tools()).tools:
            ro = tool.annotations.read_only_hint if tool.annotations else None
            lines.append(f"  {tool.name}{'  [read-only]' if ro else ''}: {tool.description.splitlines()[0]}")
            lines.append(f"    input_schema: {json.dumps(tool.input_schema['properties'])}")

        lines.append("\nRESOURCES (the application decides what to attach)")
        for res in (await client.list_resources()).resources:
            lines.append(f"  {res.uri}  {res.description}")
        for tmpl in (await client.list_resource_templates()).resource_templates:
            lines.append(f"  {tmpl.uri_template}  {tmpl.description}  (template)")

        lines.append("\nPROMPTS (the user picks these, e.g. as a slash command)")
        for prompt in (await client.list_prompts()).prompts:
            args = ", ".join(a.name for a in prompt.arguments or [])
            lines.append(f"  /{prompt.name}({args}): {prompt.description}")

        lines.append("\nCALLS")
        r = await client.call_tool("add_note", {"title": "dentist", "text": "Dentist on Friday at 15:00."})
        lines.append(f"  tools/call add_note -> {result_text(r)}")
        r = await client.call_tool("search_notes", {"query": "friday"})
        lines.append(f"  tools/call search_notes -> {r.structured_content}")
        r = await client.call_tool("add_note", {"title": "", "text": "no title"})
        lines.append(f"  tools/call add_note (bad input) -> is_error={r.is_error}: {result_text(r)}")
        index = await client.read_resource("notes://index")
        lines.append(f"  resources/read notes://index -> {index.contents[0].text.splitlines()}")
        prompt = await client.get_prompt("weekly_review", {"focus": "travel"})
        text = prompt.messages[0].content.text
        lines.append(f"  prompts/get weekly_review -> {prompt.messages[0].role} message, {len(text)} chars, ending")
        lines.append(f"    {text.splitlines()[-1]!r}")
    return lines


def main() -> None:
    logging.getLogger("mcp").setLevel(logging.CRITICAL)  # hide the server's own error log lines
    if "--stdio" in sys.argv:
        target: object = StdioServerParameters(command=sys.executable, args=[str(SERVER_FILE)])
    else:
        target = build_server()
    print("\n".join(asyncio.run(tour(target))))


if __name__ == "__main__":
    main()
