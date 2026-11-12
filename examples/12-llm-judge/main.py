"""LLM-as-judge: a rubric grader with structured verdicts, a pairwise judge that checks
for position bias, and calibration against human labels.

    python main.py                       # from this folder
    python 12-llm-judge/main.py          # from examples/

Read alongside docs/12-evaluation/12.3-llm-as-judge.md.

Offline, the "judge model" is a MockLLM driven by a simple keyword function, so the
run is repeatable. With LLM_PROVIDER=anthropic or openai, the same prompts go to a
real model and the same parser reads its verdicts.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, get_llm, user  # noqa: E402

# --------------------------------------------------------------------------- the rubric

JUDGE_SYSTEM = (
    "You grade answers written by a customer-support agent. Be strict and consistent. "
    "Judge only against the rubric and the reference facts. Do not reward length or confident tone."
)

RUBRIC = """Grade the answer on three separate criteria. Each is true or false.
- correct: the answer states every reference fact (paraphrases are fine).
- grounded: the answer adds no facts, numbers or promises that are not in the reference.
- concise: the answer is at most 60 words.
Think first, then decide. Reply with ONLY a JSON object, no other text:
{"reasoning": "<one or two sentences>", "correct": true|false, "grounded": true|false, "concise": true|false}"""


def pointwise_prompt(question: str, reference: list[str], answer: str) -> str:
    """One answer, one rubric. XML-style tags keep the parts clearly separated."""
    facts = "\n".join(f"- {f}" for f in reference)
    return (
        f"{RUBRIC}\n\n<question>\n{question}\n</question>\n\n"
        f"<reference>\n{facts}\n</reference>\n\n<answer>\n{answer}\n</answer>"
    )


@dataclass
class Verdict:
    """A parsed judge decision. `error` is set if the judge's reply could not be read."""

    reasoning: str = ""
    correct: bool = False
    grounded: bool = False
    concise: bool = False
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and self.correct and self.grounded and self.concise


def parse_verdict(text: str) -> Verdict:
    """Read the judge's JSON. Never treat an unreadable verdict as a pass."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return Verdict(error=f"no JSON object in judge reply: {text[:80]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        return Verdict(error=f"invalid JSON from judge: {exc}")
    fields = ("correct", "grounded", "concise")
    if not all(isinstance(data.get(f), bool) for f in fields):
        return Verdict(error=f"judge reply is missing a true/false field: {data}")
    return Verdict(reasoning=str(data.get("reasoning", "")), **{f: data[f] for f in fields})


def judge_pointwise(llm: LLM, question: str, reference: list[str], answer: str) -> Verdict:
    reply = llm.chat([user(pointwise_prompt(question, reference, answer))], system=JUDGE_SYSTEM, max_tokens=1000)
    return parse_verdict(reply.text)


# --------------------------------------------------------------------------- pairwise, with a position-bias check

PAIRWISE_RUBRIC = """Which answer is better for the customer? Judge correctness against the reference
first, then clarity. Length is not a reason to prefer an answer.
Reply with ONLY a JSON object: {"reasoning": "<one sentence>", "winner": "first" | "second" | "tie"}"""


def pairwise_prompt(question: str, reference: list[str], first: str, second: str) -> str:
    facts = "\n".join(f"- {f}" for f in reference)
    return (
        f"{PAIRWISE_RUBRIC}\n\n<question>\n{question}\n</question>\n\n<reference>\n{facts}\n</reference>\n\n"
        f"<first_answer>\n{first}\n</first_answer>\n\n<second_answer>\n{second}\n</second_answer>"
    )


def _winner(llm: LLM, prompt: str) -> str:
    match = re.search(r"\{.*\}", llm.chat([user(prompt)], system=JUDGE_SYSTEM, max_tokens=500).text, re.DOTALL)
    try:
        winner = json.loads(match.group(0)).get("winner") if match else None
    except json.JSONDecodeError:
        winner = None
    return winner if winner in ("first", "second", "tie") else "error"


def judge_pairwise(llm: LLM, question: str, reference: list[str], a: str, b: str) -> str:
    """Ask twice, with the answers swapped. Return "A", "B", "tie", or "inconsistent".

    If the judge's choice follows the position rather than the content, the two
    orders disagree, and we refuse to count the comparison.
    """
    first = _winner(llm, pairwise_prompt(question, reference, a, b))  # A shown first
    second = _winner(llm, pairwise_prompt(question, reference, b, a))  # B shown first
    as_letter = {("first", 1): "A", ("second", 1): "B", ("first", 2): "B", ("second", 2): "A"}
    w1 = as_letter.get((first, 1), first)
    w2 = as_letter.get((second, 2), second)
    if "error" in (w1, w2):
        return "error"
    return w1 if w1 == w2 else "inconsistent"


# --------------------------------------------------------------------------- calibration against humans


def agreement(judge: list[bool], human: list[bool]) -> float:
    """Share of cases where the judge and the human gave the same pass/fail label."""
    return sum(j == h for j, h in zip(judge, human, strict=True)) / len(human)


def cohens_kappa(judge: list[bool], human: list[bool]) -> float:
    """Agreement corrected for chance: 1 = perfect, 0 = no better than chance."""
    n = len(human)
    observed = agreement(judge, human)
    p_j, p_h = sum(judge) / n, sum(human) / n
    expected = p_j * p_h + (1 - p_j) * (1 - p_h)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


# --------------------------------------------------------------------------- offline stand-ins for a judge model


def _tag(text: str, name: str) -> str:
    match = re.search(rf"<{name}>\n(.*?)\n</{name}>", text, re.DOTALL)
    return match.group(1) if match else ""


def keyword_judge(messages: list[Message]) -> str:
    """A crude, deterministic stand-in for a judge model, so the demo runs offline.

    It checks facts by exact substring, so unlike a real model it cannot see that
    "within a week" and "5 business days" are close. Calibration will catch that.
    """
    prompt = messages[-1]["content"]
    reference = _tag(prompt, "reference")
    facts = [line[2:] for line in reference.splitlines() if line.startswith("- ")]
    if "<first_answer>" in prompt:  # pairwise: prefer the answer that states more facts
        score = [sum(f.lower() in _tag(prompt, t).lower() for f in facts) for t in ("first_answer", "second_answer")]
        winner = "tie" if score[0] == score[1] else ("first" if score[0] > score[1] else "second")
        return json.dumps({"reasoning": f"fact counts {score}", "winner": winner})
    answer = _tag(prompt, "answer")
    missing = [f for f in facts if f.lower() not in answer.lower()]
    invented = [n for n in re.findall(r"\$?\d+", answer) if n not in reference]
    verdict = {
        "reasoning": f"missing facts: {missing or 'none'}; unsupported numbers: {invented or 'none'}",
        "correct": not missing,
        "grounded": not invented,
        "concise": len(answer.split()) <= 60,
    }
    return json.dumps(verdict)


def position_biased_judge(messages: list[Message]) -> LLMResponse:
    """A judge with a strong position bias: it always prefers whatever it sees first."""
    return MockLLM.text('{"reasoning": "The first answer looks good.", "winner": "first"}')


# --------------------------------------------------------------------------- the demo data

QUESTION = "I returned my jacket. How long until I get my money back?"
REFERENCE = ["original payment method", "5 business days"]

# Answers from the agent under test, each labelled pass/fail by a person using the same rubric.
CASES: list[dict[str, Any]] = [
    {"id": "c1", "human": True,
     "answer": "Your refund goes back to your original payment method within 5 business days."},
    {"id": "c2", "human": False,
     "answer": "Refunds take 5 business days."},
    {"id": "c3", "human": True,
     "answer": "You'll see the money on your original payment method within a week (5 working days)."},
    {"id": "c4", "human": False,
     "answer": "It goes to your original payment method within 5 business days, plus a $10 voucher for the wait."},
    {"id": "c5", "human": False,
     "answer": "Great question! " + "We really value you as a customer and want you to be happy. " * 6
     + "Refunds go to your original payment method within 5 business days."},
    {"id": "c6", "human": False, "answer": "I'm not sure, sorry."},
]


def main() -> None:
    judge_llm = get_llm(mock_responses=[keyword_judge] * (len(CASES) + 2))

    print("Pointwise rubric grading")
    verdicts = []
    for case in CASES:
        v = judge_pointwise(judge_llm, QUESTION, REFERENCE, case["answer"])
        verdicts.append(v)
        flags = f"correct={v.correct!s:<5} grounded={v.grounded!s:<5} concise={v.concise!s:<5}"
        mark = "" if v.passed == case["human"] else "   <-- disagrees with human"
        line = (f"  {case['id']}: judge={'pass' if v.passed else 'fail'}  human={'pass' if case['human'] else 'fail'}"
                f"  {flags}{mark}")
        print(line.rstrip())

    judge_labels = [v.passed for v in verdicts]
    human_labels = [c["human"] for c in CASES]
    print(f"\nAgreement with human labels: {agreement(judge_labels, human_labels):.0%}")
    print(f"Cohen's kappa:               {cohens_kappa(judge_labels, human_labels):.2f}")
    for case, v in zip(CASES, verdicts):
        if v.passed != case["human"]:
            print(f"Review {case['id']}: {v.reasoning}")

    print("\nPairwise comparison of c1 (A) vs c2 (B), asked in both orders")
    print(f"  fair judge:            {judge_pairwise(judge_llm, QUESTION, REFERENCE, CASES[0]['answer'], CASES[1]['answer'])}")
    biased = MockLLM([position_biased_judge] * 2)
    print(f"  position-biased judge: {judge_pairwise(biased, QUESTION, REFERENCE, CASES[0]['answer'], CASES[1]['answer'])}")


if __name__ == "__main__":
    main()
