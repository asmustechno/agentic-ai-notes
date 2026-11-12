"""A tiny MCP server for notes: two tools, two resources and one prompt.

Run it as a real MCP server over stdio (this is what an MCP host such as an IDE
or desktop app would launch):

    python notes_server.py

It prints nothing on stdout except MCP messages, so don't expect output in your
terminal. To see it work, run `python main.py` instead, which connects a client.

Read alongside docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md.
Written for the MCP Python SDK 2.x (`mcp==2.3.0`), where `FastMCP` is now `MCPServer`.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

STARTER_NOTES = {
    "groceries": "Milk, eggs, coffee beans.",
    "trip": "Train to Lyon on Friday at 09:12, platform 4.",
}


def build_server(notes: dict[str, str] | None = None) -> MCPServer:
    """Create the notes server. Pass `notes` to start from your own data (tests do)."""
    store: dict[str, str] = dict(STARTER_NOTES if notes is None else notes)

    mcp = MCPServer(
        "notes",
        version="1.0.0",
        instructions="Personal notes. Search before you add, so you don't create duplicates.",
    )

    # ---------------------------------------------------------------- tools (model-controlled)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    def search_notes(
        query: Annotated[str, Field(description="One or more words to look for, e.g. 'friday train'.")],
    ) -> list[str]:
        """Search notes by keyword. Returns every note that contains all the words, as 'title: text'."""
        words = query.lower().split()
        return [f"{title}: {text}" for title, text in store.items() if all(w in f"{title} {text}".lower() for w in words)]

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True))
    def add_note(
        title: Annotated[str, Field(description="A short title such as 'dentist'.", max_length=40)],
        text: Annotated[str, Field(description="The full note text.")],
    ) -> str:
        """Save a note under a short title. Saving under an existing title replaces that note."""
        title = title.strip().lower()
        if not title:
            # ToolError becomes a tool result with isError: true, so the model can read it and retry.
            raise ToolError("title must not be empty")
        store[title] = text.strip()
        return f"Saved note '{title}'."

    # ---------------------------------------------------------------- resources (application-controlled)

    @mcp.resource("notes://index", description="A list of every note title.")
    def note_index() -> str:
        return "\n".join(sorted(store))

    @mcp.resource("notes://{title}", description="The full text of one note.")
    def read_note(title: str) -> str:
        if title not in store:
            raise ResourceError(f"No note called {title!r}")
        return store[title]

    # ---------------------------------------------------------------- prompts (user-controlled)

    @mcp.prompt()
    def weekly_review(focus: str = "anything time-sensitive") -> str:
        """Review all notes and suggest what to do this week."""
        return (
            "Here are my notes:\n\n"
            + "\n".join(f"- {t}: {x}" for t, x in sorted(store.items()))
            + f"\n\nGive me a short plan for this week. Focus on {focus}."
        )

    return mcp


mcp = build_server()

if __name__ == "__main__":
    mcp.run()  # stdio by default; mcp.run(transport="streamable-http") serves http://127.0.0.1:8000/mcp
