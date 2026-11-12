"""Chain-of-thought by prompting: ask for reasoning in <thinking> tags and the result in <answer> tags.

    python main.py                         # from this folder
    python 07-chain-of-thought/main.py     # from examples/

Shows two prompts for the same word problem (from Wei et al., 2022, Figure 1):

  1. direct:            "answer with just the number";
  2. chain-of-thought:  "think step by step in <thinking>, then put the result in <answer>".

Your code keeps the reasoning for logs and shows the user only the <answer>.

Offline, MockLLM replays scripted replies that mirror the paper's figure: older models
often got this wrong when asked for the answer alone. Current models usually get it right
either way, because they reason internally ("extended thinking"). Try a real one:

    LLM_PROVIDER=anthropic ANTHROPIC_EFFORT=low python main.py

Read alongside docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

QUESTION = (
    "The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, how many apples do they have?"
)

DIRECT_SYSTEM = "Answer with just the number. No explanation."

COT_SYSTEM = (
    "Solve the problem. First think it through step by step inside <thinking></thinking> tags. "
    "Then give only the final result inside <answer></answer> tags."
)


@dataclass
class Result:
    answer: str  # what we show the user
    reasoning: str  # what we keep for logs and debugging (empty if none)
    output_tokens: int


def extract(text: str) -> tuple[str, str]:
    """Split a reply into (answer, reasoning). Falls back to the whole text if the tags are missing."""
    thinking = re.search(r"<thinking>(.*?)</thinking>", text, re.S)
    answer = re.search(r"<answer>(.*?)</answer>", text, re.S)
    reasoning = thinking.group(1).strip() if thinking else ""
    if answer:
        return answer.group(1).strip(), reasoning
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.S).strip(), reasoning


def ask(llm: LLM, question: str, *, chain_of_thought: bool) -> Result:
    reply = llm.chat([user(question)], system=COT_SYSTEM if chain_of_thought else DIRECT_SYSTEM)
    answer, reasoning = extract(reply.text)
    return Result(answer, reasoning, reply.usage.output_tokens)


SCRIPT = [
    "27",  # direct: the mistake shown in the paper's figure for standard prompting
    "<thinking>The cafeteria started with 23 apples. They used 20, so 23 - 20 = 3. "
    "They bought 6 more, so 3 + 6 = 9.</thinking>\n<answer>9</answer>",
]


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    print(f"Q: {QUESTION}\n")
    direct = ask(llm, QUESTION, chain_of_thought=False)
    print(f"1) Direct            answer: {direct.answer:4} (output tokens: {direct.output_tokens})")
    cot = ask(llm, QUESTION, chain_of_thought=True)
    print(f"2) Chain-of-thought  answer: {cot.answer:4} (output tokens: {cot.output_tokens})")
    print(f"   reasoning kept for logs: {cot.reasoning}")


if __name__ == "__main__":
    main()
