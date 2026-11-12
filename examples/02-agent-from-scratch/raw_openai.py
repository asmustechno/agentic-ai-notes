"""The same agent written directly against the OpenAI SDK (Chat Completions, no wrapper).

Needs OPENAI_API_KEY and OPENAI_MODEL:   python raw_openai.py
The tests run it offline with a fake client.
"""

from __future__ import annotations

import json
import os
from typing import Any

FILES = {
    "README.md": "Demo service. See config/ for settings.",
    "config/app.toml": "[server]\nport = 8080\nworkers = 4",
}
TOOLS = [  # OpenAI wraps each tool in {"type": "function", "function": {...}} and calls the schema "parameters"
    {"type": "function", "function": {"name": "list_files", "description": "List every file path in the project.",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "read_file",
                                      "description": "Read one file. Use an exact path returned by list_files.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                                     "required": ["path"]}}},
]


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Run one tool. OpenAI has no is_error flag, so failures say "Error" in words."""
    if name == "list_files":
        return "\n".join(FILES)
    if name == "read_file" and args.get("path") in FILES:
        return FILES[args["path"]]
    return f"Error: cannot run {name} with {args}"


def run_agent(goal: str, client: Any = None, model: str | None = None, max_steps: int = 10) -> str:
    if client is None:
        from openai import OpenAI

        client = OpenAI()  # reads OPENAI_API_KEY
    model = model or os.environ["OPENAI_MODEL"]
    messages: list[Any] = [
        {"role": "system", "content": "You answer questions about a code project. Use the tools; never guess."},
        {"role": "user", "content": goal},
    ]
    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS, max_completion_tokens=16000
        )
        message = response.choices[0].message
        messages.append(message)  # the SDK accepts its own message object back in the history
        if not message.tool_calls:
            return message.content or ""
        for call in message.tool_calls:
            try:
                args = json.loads(call.function.arguments)  # arguments arrive as a JSON *string*
            except json.JSONDecodeError as exc:
                output = f"Error: arguments were not valid JSON ({exc})"
            else:
                output = run_tool(call.function.name, args)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})  # one message per result
    return "Stopped: reached the step limit before finishing."


if __name__ == "__main__":
    print(run_agent("Which port does the web server listen on?"))
