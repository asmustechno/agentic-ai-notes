"""The evaluator-optimizer loop: a generator writes, a separate evaluator grades against a rubric.

    generator  : its own model and prompt; writes a draft, then revises from feedback
    evaluator  : its own model and prompt; returns JSON {"pass": bool, "feedback": str}
    hard checks: plain Python rules (word count, required text) that run before the evaluator

The loop stops as soon as a draft passes, or after `max_rounds`, returning the best attempt.
`optimize()` is a reusable building block: pass it any generate and evaluate functions.

    python main.py                           # from this folder
    python 08-evaluator-optimizer/main.py    # from examples/

Read alongside docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md
and docs/09-agent-design-patterns/09.5-evaluator-optimizer.md.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

# --------------------------------------------------------------------------- the reusable loop


@dataclass
class Verdict:
    """What the evaluator decided about one draft."""

    passed: bool
    score: int  # 0-100, used to pick the best draft if none passes
    feedback: str


@dataclass
class Round:
    draft: str
    verdict: Verdict


@dataclass
class OptimizeResult:
    best: str
    passed: bool
    rounds: list[Round] = field(default_factory=list)


def optimize(
    generate: Callable[[str | None, str | None], str],
    evaluate: Callable[[str], Verdict],
    *,
    max_rounds: int = 3,
) -> OptimizeResult:
    """Generate, evaluate, and regenerate with feedback until a draft passes or rounds run out.

    `generate(previous_draft, feedback)` is called with (None, None) the first time.
    """
    rounds: list[Round] = []
    draft, feedback = None, None
    for _ in range(max_rounds):
        draft = generate(draft, feedback)
        verdict = evaluate(draft)
        rounds.append(Round(draft, verdict))
        if verdict.passed:
            return OptimizeResult(best=draft, passed=True, rounds=rounds)
        feedback = verdict.feedback
    best = max(rounds, key=lambda r: r.verdict.score)  # nothing passed: return the best attempt, flagged
    return OptimizeResult(best=best.draft, passed=False, rounds=rounds)


# --------------------------------------------------------------------------- one concrete use: a customer email

ORDER_ID = "A-1042"
MAX_WORDS = 50
BRIEF = (
    f"Write a short email to a customer whose order {ORDER_ID} is delayed by 3 days because of a "
    "warehouse problem. Apologise, give the new delivery estimate (Friday), and offer the discount "
    f"code SORRY10 for 10% off their next order. Mention the order number. Keep it under {MAX_WORDS} words."
)

GENERATOR_SYSTEM = "You write warm, clear customer-service emails. Reply with the email only."

RUBRIC = """\
1. Apologises sincerely, without blaming the customer or making excuses at length.
2. States the new delivery estimate.
3. Offers the discount code SORRY10 and says what it is worth.
4. Friendly, plain language; no jargon."""

EVALUATOR_SYSTEM = (
    "You grade customer-service emails against a rubric. Be strict: a criterion that is only "
    "partly met is not met. Reply with JSON only, in this shape:\n"
    '{"pass": true or false, "score": 0-100, "feedback": "one line per unmet criterion, saying how to fix it"}'
)


def hard_checks(email: str) -> list[str]:
    """Rules code can check exactly. Cheaper and more reliable than asking a model."""
    problems = []
    words = len(email.split())
    if words > MAX_WORDS:
        problems.append(f"Too long: {words} words, the limit is {MAX_WORDS}.")
    if ORDER_ID not in email:
        problems.append(f"Must mention the order number {ORDER_ID}.")
    return problems


def parse_verdict(text: str) -> Verdict:
    """Parse the evaluator's JSON. Anything unparseable counts as a fail, never as a pass."""
    match = re.search(r"\{.*\}", text, re.S)  # tolerate ```json fences or a sentence around the JSON
    try:
        data = json.loads(match.group(0) if match else text)
        return Verdict(passed=data["pass"] is True, score=int(data.get("score", 0)), feedback=str(data["feedback"]))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return Verdict(passed=False, score=0, feedback=f"Evaluator reply was not valid JSON: {text[:200]}")


def make_generator(llm: LLM) -> Callable[[str | None, str | None], str]:
    def generate(previous: str | None, feedback: str | None) -> str:
        if previous is None:
            prompt = BRIEF
        else:
            prompt = (
                f"{BRIEF}\n\nYour previous draft:\n{previous}\n\n"
                f"A reviewer said:\n{feedback}\n\nWrite an improved email that fixes every point."
            )
        return llm.chat([user(prompt)], system=GENERATOR_SYSTEM).text.strip()

    return generate


@dataclass
class Evaluator:
    """Hard checks first, then the evaluator model with the rubric. Counts its own model calls."""

    llm: LLM
    model_calls: int = 0

    def __call__(self, email: str) -> Verdict:
        problems = hard_checks(email)
        if problems:  # fail fast: no need to pay for a model call
            return Verdict(passed=False, score=0, feedback="\n".join(problems))
        self.model_calls += 1
        reply = self.llm.chat([user(f"Rubric:\n{RUBRIC}\n\nEmail to grade:\n{email}")], system=EVALUATOR_SYSTEM)
        return parse_verdict(reply.text)


DRAFT_1 = (
    "Dear customer, we are very sorry. Unfortunately, due to an unexpected and highly unusual issue at "
    "our main fulfilment warehouse, which our operations team is currently investigating as a matter of "
    "priority, your recent order has been delayed. We now expect it to arrive on Friday. We truly value "
    "your business and apologise for any inconvenience this may have caused you and your family."
)
DRAFT_2 = (
    f"Hi there, I'm sorry: your order {ORDER_ID} is running 3 days late because of a problem at our "
    "warehouse. It should now arrive on Friday. We appreciate your patience."
)
DRAFT_3 = (
    f"Hi there, I'm sorry: your order {ORDER_ID} is running 3 days late because of a problem at our "
    "warehouse. It should now arrive on Friday. As a thank-you for your patience, use code SORRY10 "
    "for 10% off your next order."
)
GENERATOR_SCRIPT = [DRAFT_1, DRAFT_2, DRAFT_3]
EVALUATOR_SCRIPT = [
    # draft 1 fails the hard checks, so the evaluator model is not called for it
    '{"pass": false, "score": 60, "feedback": "Criterion 3 unmet: offer the code SORRY10 and say it gives 10% off."}',
    '{"pass": true, "score": 95, "feedback": "All criteria met."}',
]


def main() -> None:
    generator_llm = get_llm(mock_responses=GENERATOR_SCRIPT)
    evaluator_llm = get_llm(mock_responses=EVALUATOR_SCRIPT)  # in production, often a different model
    evaluator = Evaluator(evaluator_llm)
    result = optimize(make_generator(generator_llm), evaluator, max_rounds=3)

    for i, r in enumerate(result.rounds, start=1):
        status = "PASS" if r.verdict.passed else "FAIL"
        print(f"--- round {i}: {len(r.draft.split())} words -> {status} (score {r.verdict.score})")
        print(r.draft)
        print(f"feedback: {r.verdict.feedback}\n")
    print(f"Result: {'passed' if result.passed else 'best attempt, did NOT pass'} after {len(result.rounds)} round(s).")
    print(f"Model calls: generator {len(result.rounds)}, evaluator {evaluator.model_calls}")


if __name__ == "__main__":
    main()
