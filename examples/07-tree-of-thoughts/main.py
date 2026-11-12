"""Tree of thoughts (breadth-first) on the Game of 24, the task used by Yao et al. (2023).

    python main.py                          # from this folder
    python 07-tree-of-thoughts/main.py      # from examples/

Goal: use each of four numbers once, with + - * /, to make 24. Input: 4 9 10 13.

A "thought" is one arithmetic step, e.g. "13 - 9 = 4 (left: 4 4 10)". Each round:

  1. PROPOSE   the model suggests next steps for every state on the frontier;
  2. CHECK     our code throws away proposals with wrong arithmetic;
  3. EVALUATE  the model rates each new state: sure / likely / impossible to reach 24;
  4. PRUNE     keep the best `breadth` states and go one level deeper.

Offline, MockLLM stands in for the model with small Python functions: the proposer
lists possible steps, and the evaluator uses rough "too big / too small" rules, like the
commonsense checks the paper asks the model to make. It is not a perfect oracle, so
the search still has to work. With a real model, set LLM_PROVIDER (it makes many calls).

Read alongside docs/07-planning-and-reasoning/07.4-tree-of-thoughts.md.
"""

from __future__ import annotations

import itertools
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, get_llm, user  # noqa: E402

# --------------------------------------------------------------------------- states and thoughts


@dataclass(frozen=True)
class State:
    numbers: tuple[int, ...]  # numbers still to use
    steps: tuple[str, ...] = ()  # the thoughts that led here

    def show(self) -> str:
        return " ".join(map(str, self.numbers))


def apply(a: int, op: str, b: int) -> int | None:
    """Do one operation. We keep to whole numbers to stay simple, so a / b only if it divides exactly."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b if a >= b else None
    if op == "*":
        return a * b
    if op == "/":
        return a // b if b and a % b == 0 else None
    return None


THOUGHT = re.compile(r"(-?\d+)\s*([+\-*/])\s*(-?\d+)\s*=\s*(-?\d+)\s*\(left:\s*([\d\s]*)\)")


def check(state: State, line: str) -> State | None:
    """Parse a proposed thought and verify it. Models make arithmetic slips; never trust, always check."""
    m = THOUGHT.search(line)
    if not m:
        return None
    a, op, b, result = int(m[1]), m[2], int(m[3]), int(m[4])
    left = tuple(sorted(int(x) for x in m[5].split()))
    remaining = list(state.numbers)
    for n in (a, b):
        if n not in remaining:
            return None
        remaining.remove(n)
    if apply(a, op, b) != result or tuple(sorted(remaining + [result])) != left:
        return None
    return State(left, state.steps + (f"{a} {op} {b} = {result} (left: {' '.join(map(str, left))})",))


# --------------------------------------------------------------------------- prompts

PROPOSE_PROMPT = """Propose possible next steps for the Game of 24. Use exactly two of the numbers and one of + - * /.
Write one step per line, in this format:  a op b = c (left: remaining numbers)
Input: {numbers}"""

EVALUATE_PROMPT = """Evaluate if these numbers can reach 24 using each exactly once with + - * /.
Reason briefly ("too big", "too small", or try a few combinations), then end with one word: sure, likely or impossible.
Numbers: {numbers}"""

VALUES = {"sure": 20.0, "likely": 1.0, "impossible": 0.0}


@dataclass
class TreeOfThoughts:
    llm: LLM
    breadth: int = 3  # states kept per level (the paper's b)
    max_proposals: int = 20  # thoughts kept per state per round
    log: list[str] = field(default_factory=list)

    def propose(self, state: State) -> list[State]:
        reply = self.llm.chat([user(PROPOSE_PROMPT.format(numbers=state.show()))])
        children = [c for line in reply.text.splitlines() if (c := check(state, line))]
        return children[: self.max_proposals]

    def evaluate(self, state: State) -> float:
        if len(state.numbers) == 1:  # no model needed for the last step
            return VALUES["sure"] if state.numbers[0] == 24 else VALUES["impossible"]
        reply = self.llm.chat([user(EVALUATE_PROMPT.format(numbers=state.show()))])
        words = re.findall(r"[a-z]+", reply.text.lower())
        return VALUES.get(words[-1], 0.0) if words else 0.0

    def solve(self, numbers: list[int]) -> State | None:
        frontier = [State(tuple(sorted(numbers)))]
        for depth in range(1, len(numbers)):
            candidates = [child for state in frontier for child in self.propose(state)]
            scored = sorted(((self.evaluate(c), c) for c in set(candidates)), key=lambda p: (-p[0], p[1].steps))
            frontier, seen = [], set()
            for value, c in scored:  # keep the best few, skipping dead ends and duplicate number sets
                if value > 0 and c.numbers not in seen and len(frontier) < self.breadth:
                    frontier.append(c)
                    seen.add(c.numbers)
            self.log.append(f"depth {depth}: {len(candidates)} proposals, kept "
                            + (", ".join(f"[{c.show()}]" for c in frontier) or "nothing"))
            if not frontier:
                return None
        return next((s for s in frontier if s.numbers == (24,)), None)


# --------------------------------------------------------------------------- offline stand-in for the model


def _numbers(messages: list[Message], label: str) -> list[int]:
    line = next(ln for ln in messages[-1]["content"].splitlines() if ln.startswith(label))
    return [int(x) for x in line.split(":", 1)[1].split()]


def mock_propose(nums: list[int]) -> str:
    """List every valid whole-number step (a real model proposes a handful, not all)."""
    lines = []
    for i, j in itertools.permutations(range(len(nums)), 2):
        for op in "+-*/":
            result = apply(nums[i], op, nums[j])
            if result is None or (op in "+*" and i > j):  # skip mirror images of + and *
                continue
            left = sorted([n for k, n in enumerate(nums) if k not in (i, j)] + [result])
            lines.append(f"{nums[i]} {op} {nums[j]} = {result} (left: {' '.join(map(str, left))})")
    return "\n".join(lines)


def _reaches_24(a: int, b: int) -> bool:
    return 24 in {a + b, abs(a - b), a * b} or (min(a, b) > 0 and max(a, b) == 24 * min(a, b))


def mock_evaluate(nums: list[int]) -> str:
    """Rough checks, like the paper's evaluator prompt: a quick look-ahead with + - * only,
    then "too big / too small" rules of thumb. It misses answers that need division."""
    if len(nums) == 2:
        return "24 is reachable: sure" if _reaches_24(*nums) else "No operation gives 24: impossible"
    for i, j in itertools.combinations(range(len(nums)), 2):
        rest = [n for k, n in enumerate(nums) if k not in (i, j)]
        for value in {nums[i] + nums[j], abs(nums[i] - nums[j]), nums[i] * nums[j]}:
            if len(rest) == 1 and _reaches_24(value, rest[0]):
                return f"Found a way through {value}: sure"
    if max(nums) > 24 * 4 or sum(nums) * max(nums) < 24:
        return "The numbers are too big or too small: impossible"
    return "Hard to say without trying more: likely"


def mock_model(messages: list[Message]) -> str:
    text = messages[-1]["content"]
    if text.startswith("Propose"):
        return mock_propose(_numbers(messages, "Input"))
    return mock_evaluate(_numbers(messages, "Numbers"))


PUZZLE = [4, 9, 10, 13]


def main() -> None:
    llm = get_llm(mock_responses=[mock_model] * 200)
    tot = TreeOfThoughts(llm)
    print(f"Input: {' '.join(map(str, PUZZLE))}\n")
    solution = tot.solve(PUZZLE)
    print("\n".join(tot.log))
    calls = getattr(llm, "calls", [])
    if calls:
        print(f"\nModel calls: {len(calls)} (one chain-of-thought attempt would be 1)")
    print("\nSolution:" if solution else "\nNo solution found.")
    for step in solution.steps if solution else ():
        print(f"  {step}")


if __name__ == "__main__":
    main()
