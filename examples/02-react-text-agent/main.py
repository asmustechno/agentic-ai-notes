"""A ReAct agent in the original text format: Thought, Action, Observation.

The model writes plain text. Our code finds the line `Action: tool[input]`,
runs that tool, and replies with `Observation: ...`. No native tool calling is
used: this is how ReAct worked in the 2022 paper (Yao et al., arXiv 2210.03629).
Modern APIs do the same thing with structured tool calls (see 2.3 and 3.3).

    python main.py                         # from this folder
    python 02-react-text-agent/main.py     # from examples/

Read alongside docs/02-the-agent-loop/02.2-react-explained.md.
"""

from __future__ import annotations

import ast
import operator
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, get_llm, user  # noqa: E402

# --------------------------------------------------------------------------- tools (plain functions: str -> str)

FAKE_ENCYCLOPEDIA = {
    "eiffel tower": "The Eiffel Tower is a wrought-iron tower in Paris. It was completed in 1889 for the World's Fair.",
    "empire state building": "The Empire State Building is a skyscraper in New York City. It opened in 1931.",
    "big ben": "Big Ben is the nickname for the Great Bell of the clock at the Palace of Westminster, London.",
}


def search(query: str) -> str:
    """Look up a short encyclopedia entry (fake data for the demo)."""
    q = query.strip().lower()
    for title, text in FAKE_ENCYCLOPEDIA.items():
        if q in title or title in q:
            return text
    return f"No entry for '{query}'. Try a shorter, more specific name."


_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> str:
    """Evaluate simple arithmetic safely (numbers and + - * / only, no eval())."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("only numbers and + - * / are allowed")

    try:
        return str(ev(ast.parse(expression, mode="eval").body))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"Error: {exc}"


TOOLS: dict[str, Callable[[str], str]] = {"search": search, "calculate": calculate}

# --------------------------------------------------------------------------- the ReAct prompt

SYSTEM = """Answer the question by repeating Thought, Action and Observation steps.

Use exactly this format, one step at a time:
Thought: <your reasoning about what to do next>
Action: <action>[<input>]

Available actions:
- search[name]: look up a short encyclopedia entry about a person, place or thing.
- calculate[expression]: evaluate arithmetic such as 12 * (3 + 4).
- finish[answer]: give the final answer and stop.

Write one Thought and one Action, then stop. I will reply with the Observation.
Never write an Observation yourself."""

ACTION_RE = re.compile(r"^\s*Action\s*:\s*(\w+)\s*\[(.*)\]\s*$", re.MULTILINE | re.IGNORECASE)
THOUGHT_RE = re.compile(r"^\s*Thought\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
FORMAT_HELP = "Invalid format. Reply with one 'Thought: ...' line and one 'Action: action[input]' line."


def strip_invented_observation(text: str) -> str:
    """Cut the reply at any 'Observation:' the model wrote itself.

    Without a stop sequence, models often carry on and *imagine* the tool's result.
    Only observations produced by our code may enter the history.
    """
    match = re.search(r"^\s*Observation\s*:", text, re.MULTILINE | re.IGNORECASE)
    return text[: match.start()].rstrip() if match else text.strip()


def parse_step(text: str) -> tuple[str, tuple[str, str] | None]:
    """Return (thought, (action, input)) from one model reply. Action is None if missing."""
    thought = THOUGHT_RE.search(text)
    action = ACTION_RE.search(text)
    return (
        thought.group(1).strip() if thought else "",
        (action.group(1).lower(), action.group(2).strip()) if action else None,
    )


# --------------------------------------------------------------------------- the loop


@dataclass
class ReActResult:
    answer: str | None  # None if the agent ran out of steps
    steps: int
    trace: list[str] = field(default_factory=list)


def run_react(llm: LLM, question: str, *, max_steps: int = 6) -> ReActResult:
    """Run Thought -> Action -> Observation until finish[...] or the step limit."""
    messages: list[Message] = [user(f"Question: {question}")]
    trace: list[str] = []
    for step in range(1, max_steps + 1):
        reply = llm.chat(messages, system=SYSTEM)  # no tools=...: the model only writes text
        text = strip_invented_observation(reply.text)
        messages.append({"role": "assistant", "content": text})

        thought, action = parse_step(text)
        trace.append(f"Thought {step}: {thought}")
        if action is None:
            observation = FORMAT_HELP
        else:
            name, arg = action
            trace.append(f"Action {step}: {name}[{arg}]")
            if name == "finish":
                return ReActResult(answer=arg, steps=step, trace=trace)
            tool = TOOLS.get(name)
            observation = tool(arg) if tool else f"Unknown action '{name}'. Use one of: search, calculate, finish."
        trace.append(f"Observation {step}: {observation}")
        messages.append(user(f"Observation: {observation}"))
    return ReActResult(answer=None, steps=max_steps, trace=trace)


# --------------------------------------------------------------------------- demo

QUESTION = "How many years after the Eiffel Tower was completed did the Empire State Building open?"
SCRIPT = [
    # Step 1: the model also *invents* an observation (with a wrong year). Our code cuts it off.
    "Thought: I need the year the Eiffel Tower was completed.\n"
    "Action: search[Eiffel Tower]\n"
    "Observation: The Eiffel Tower was completed in 1887.",
    "Thought: The Eiffel Tower was completed in 1889. Now I need the year the Empire State Building opened.\n"
    "Action: search[Empire State Building]",
    "Thought: It opened in 1931. The gap is 1931 minus 1889.\nAction: calculate[1931 - 1889]",
    "Thought: The difference is 42 years.\n"
    "Action: finish[42 years. The Eiffel Tower was completed in 1889 and the Empire State Building opened in 1931.]",
]


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    print(f"Question: {QUESTION}\n")
    result = run_react(llm, QUESTION)
    print("\n".join(result.trace))
    print(f"\nAnswer after {result.steps} steps: {result.answer}")


if __name__ == "__main__":
    main()
