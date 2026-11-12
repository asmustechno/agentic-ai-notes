"""The same agent written directly against the Anthropic SDK (no wrapper).

Needs ANTHROPIC_API_KEY:   python raw_anthropic.py
The tests run it offline with a fake client.

This follows the manual agentic loop in Anthropic's docs. For real projects the
SDK also has a tool runner (beta) that writes this loop for you.
"""

from __future__ import annotations

from typing import Any

FILES = {
    "README.md": "Demo service. See config/ for settings.",
    "config/app.toml": "[server]\nport = 8080\nworkers = 4",
}
TOOLS = [
    {"name": "list_files", "description": "List every file path in the project.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_file", "description": "Read one file. Use an exact path returned by list_files.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]


def run_tool(name: str, args: dict[str, Any]) -> tuple[str, bool]:
    """Run one tool. Returns (output, is_error)."""
    if name == "list_files":
        return "\n".join(FILES), False
    if name == "read_file" and args.get("path") in FILES:
        return FILES[args["path"]], False
    return f"Error: cannot run {name} with {args}", True


def run_agent(goal: str, client: Any = None, model: str = "claude-opus-5-5", max_steps: int = 10) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    messages: list[dict[str, Any]] = [{"role": "user", "content": goal}]
    for _ in range(max_steps):
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system="You answer questions about a code project. Use the tools; never guess.",
            tools=TOOLS,
            messages=messages,
        )
        # Append the assistant turn exactly as received: it holds the tool_use blocks.
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":  # end_turn (or max_tokens, refusal: see 2.4)
            return "".join(b.text for b in response.content if b.type == "text")
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output, is_error = run_tool(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})  # ALL results in ONE user message
    return "Stopped: reached the step limit before finishing."


if __name__ == "__main__":
    print(run_agent("Which port does the web server listen on?"))
