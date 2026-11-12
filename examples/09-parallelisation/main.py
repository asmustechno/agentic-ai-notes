"""Parallelisation: run independent LLM calls at the same time, then combine them in code.

    sectioning : split one job into DIFFERENT independent parts (security, performance, readability
                 reviews of the same code), run them concurrently, merge the results
    voting     : ask the SAME question several times (here with reworded prompts), count the answers,
                 and decide with a threshold

LLM calls spend most of their time waiting on the network, so threads are enough:
concurrent.futures.ThreadPoolExecutor runs them side by side.

    python main.py                       # from this folder
    python 09-parallelisation/main.py    # from examples/

Read alongside docs/09-agent-design-patterns/09.3-parallelisation.md.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, get_llm, user  # noqa: E402

T = TypeVar("T")
R = TypeVar("R")

CODE = '''\
def find_user(db, name):
    rows = db.execute(f"SELECT * FROM users WHERE name = '{name}'")
    for row in rows:
        if row["name"] == name:
            return row
'''


def run_parallel(
    fn: Callable[[T], R], items: list[T], *, max_workers: int = 8, timeout: float = 120
) -> list[R | Exception]:
    """Call fn(item) for every item concurrently. Results keep the input order; a failure becomes its exception."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fn, item) for item in items]
        results: list[R | Exception] = []
        for future in futures:
            try:
                results.append(future.result(timeout=timeout))
            except Exception as exc:  # one failed call must not lose the others
                results.append(exc)
        return results


# ---------------------------------------------------------------- sectioning

ASPECTS = {
    "security": "Look ONLY for security problems.",
    "performance": "Look ONLY for performance problems.",
    "readability": "Look ONLY for readability and maintainability problems.",
}


def review_aspect(llm: LLM, code: str, aspect: str) -> str:
    return llm.chat(
        [user(f"Aspect: {aspect}\n\nCode:\n{code}")],
        system=f"You are a code reviewer. {ASPECTS[aspect]} Reply with at most two short bullet points, or 'none'.",
    ).text.strip()


def sectioned_review(llm: LLM, code: str) -> dict[str, str]:
    """Three focused reviews at once, merged into one report by plain code."""
    aspects = list(ASPECTS)
    results = run_parallel(lambda a: review_aspect(llm, code, a), aspects)
    return {a: (r if isinstance(r, str) else f"(review failed: {r})") for a, r in zip(aspects, results)}


# ---------------------------------------------------------------- voting

VOTE_PROMPTS = [
    "Is this code vulnerable to SQL injection?",
    "Could a user-supplied value change the meaning of the SQL query in this code?",
    "Would a security auditor flag this code for SQL injection?",
]


@dataclass
class VoteResult:
    yes: int
    no: int
    abstain: int
    flagged: bool


def parse_vote(text: str) -> str:
    word = text.strip().split(maxsplit=1)[0].strip(".,:!").upper() if text.strip() else ""
    return word if word in {"YES", "NO"} else "ABSTAIN"  # anything else is not counted as a vote


def vote(llm: LLM, code: str, *, n: int = 5, threshold: int = 3) -> VoteResult:
    """Ask n times (cycling through reworded prompts) and flag if at least `threshold` say YES."""
    prompts = [VOTE_PROMPTS[i % len(VOTE_PROMPTS)] for i in range(n)]
    replies = run_parallel(
        lambda q: llm.chat([user(f"{q}\n\nCode:\n{code}")], system="Answer YES or NO first, then one sentence.").text,
        prompts,
    )
    counts = Counter(parse_vote(r) if isinstance(r, str) else "ABSTAIN" for r in replies)
    return VoteResult(counts["YES"], counts["NO"], counts["ABSTAIN"], counts["YES"] >= threshold)


# ---------------------------------------------------------------- an offline demo with simulated latency

MOCK_REVIEWS = {
    "security": "- SQL injection: `name` is put straight into the query. Use a parameterised query.",
    "performance": "- Fetches every column and filters in Python. Select only needed columns and let SQL filter.",
    "readability": "- Returns None silently when no user matches. Say so in a docstring or raise an error.",
}
MOCK_VOTES = [
    "YES. The name is formatted into the SQL string.",
    "YES, a quote in the name breaks out of the string.",
    "NO. It looks like an internal helper.",
    "YES. An auditor would flag the f-string query.",
    "Possibly, it depends on the driver.",
]


def slow(reply: str | Callable[[list[Message]], str], delay: float) -> Callable[[list[Message]], str]:
    """Wrap a scripted reply so it takes `delay` seconds, like a real network call."""

    def respond(messages: list[Message]) -> str:
        time.sleep(delay)
        return reply(messages) if callable(reply) else reply

    return respond


def mock_review(messages: list[Message]) -> str:
    aspect = messages[-1]["content"].split("\n", 1)[0].removeprefix("Aspect: ")
    return MOCK_REVIEWS[aspect]


def main(delay: float = 0.5) -> None:
    llm = get_llm(mock_responses=[slow(mock_review, delay)] * 6 + [slow(v, delay) for v in MOCK_VOTES])

    start = time.perf_counter()
    for aspect in ASPECTS:  # one after another, for comparison
        review_aspect(llm, CODE, aspect)
    sequential = time.perf_counter() - start

    start = time.perf_counter()
    report = sectioned_review(llm, CODE)  # the same three calls, at once
    parallel = time.perf_counter() - start

    print("SECTIONING: three focused reviews of the same code")
    for aspect, text in report.items():
        print(f"  [{aspect}] {text}")
    print(f"  time: sequential {sequential:.1f}s, parallel {parallel:.1f}s\n")

    result = vote(llm, CODE, n=5, threshold=3)
    print("VOTING: 'is this SQL injection?' asked 5 times, flag at 3 or more YES")
    print(f"  YES {result.yes}, NO {result.no}, abstain {result.abstain} -> flagged: {result.flagged}")


if __name__ == "__main__":
    main()
