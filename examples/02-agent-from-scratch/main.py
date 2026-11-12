"""A complete agent in about 50 lines of code, with no framework.

    python main.py                           # from this folder
    python 02-agent-from-scratch/main.py     # from examples/

Read alongside docs/02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md.
raw_anthropic.py and raw_openai.py are the same agent written straight
against each provider's SDK, so you can see what the shared wrapper hides.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, MockLLM, get_llm, tool_result, user  # noqa: E402

# 1. Tools: plain functions, plus a description the model reads.
FILES = {
    "README.md": "Demo service. See config/ for settings.",
    "config/app.toml": "[server]\nport = 8080\nworkers = 4",
    "config/db.toml": "[database]\nhost = 'localhost'\nport = 5432",
}


def list_files() -> str:
    return "\n".join(FILES)


def read_file(path: str) -> str:
    return FILES[path]  # an unknown path raises KeyError; the loop turns it into an error result


TOOLS = {
    "list_files": (list_files, {
        "name": "list_files",
        "description": "List every file path in the project.",
        "input_schema": {"type": "object", "properties": {}},
    }),
    "read_file": (read_file, {
        "name": "read_file",
        "description": "Read one file. Use an exact path returned by list_files.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }),
}


# 2. The loop: think (call the model), act (run its tool calls), observe (send results back).
def run_agent(llm: LLM, goal: str, system: str = "", max_steps: int = 10, trace: list | None = None) -> str:
    messages = [user(goal)]
    specs = [spec for _, spec in TOOLS.values()]
    for _ in range(max_steps):
        reply = llm.chat(messages, system=system, tools=specs)  # think
        messages.append(reply.to_message())
        if not reply.tool_calls:  # no tool requested: this is the final answer
            return reply.text
        for call in reply.tool_calls:  # act
            fn, _ = TOOLS.get(call.name, (None, None))
            try:
                output, failed = (fn(**call.arguments), False) if fn else (f"Unknown tool {call.name!r}", True)
            except Exception as exc:  # a failing tool must not crash the run
                output, failed = f"Error: {type(exc).__name__}: {exc}", True
            messages.append(tool_result(call.id, output, is_error=failed))  # observe
            if trace is not None:
                trace.append(f"{call.name}({call.arguments}) -> {output!r}")
    return "Stopped: reached the step limit before finishing."


# 3. Run it.
SYSTEM = "You answer questions about a code project. Use the tools to look at files; never guess."
GOAL = "Which port does the web server listen on?"
SCRIPT = [
    MockLLM.tool_call("list_files"),
    MockLLM.tool_call("read_file", {"path": "config/app.toml"}),
    "The web server listens on port 8080 (set in config/app.toml).",
]

if __name__ == "__main__":
    steps: list[str] = []
    answer = run_agent(get_llm(mock_responses=SCRIPT), GOAL, SYSTEM, trace=steps)
    print(f"Goal: {GOAL}\n", *steps, f"\nAnswer: {answer}", sep="\n")
