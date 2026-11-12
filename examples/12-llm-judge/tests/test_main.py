"""The judge prompt, verdict parser, pairwise swap and calibration maths. Offline, with MockLLM."""

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)

GOOD = main.CASES[0]["answer"]
INCOMPLETE = main.CASES[1]["answer"]


def test_prompt_contains_rubric_reference_and_answer() -> None:
    llm = MockLLM([main.keyword_judge])
    main.judge_pointwise(llm, main.QUESTION, main.REFERENCE, GOOD)
    sent = llm.calls[0]
    prompt = sent["messages"][0]["content"]
    assert "<reference>\n- original payment method\n- 5 business days\n</reference>" in prompt
    assert f"<answer>\n{GOOD}\n</answer>" in prompt
    assert "Do not reward length" in sent["system"]


def test_verdict_parsing_accepts_json_wrapped_in_text() -> None:
    v = main.parse_verdict('Here you go:\n{"reasoning": "ok", "correct": true, "grounded": true, "concise": true}')
    assert v.passed and v.reasoning == "ok"


@pytest.mark.parametrize(
    "reply",
    [
        "Looks good to me!",  # no JSON at all
        '{"correct": true, "grounded": true',  # truncated JSON
        '{"correct": "yes", "grounded": true, "concise": true}',  # wrong type
        '{"correct": true, "grounded": true}',  # missing field
    ],
)
def test_unreadable_verdicts_never_pass(reply: str) -> None:
    v = main.parse_verdict(reply)
    assert v.error is not None and not v.passed


def test_judge_grades_each_criterion_separately() -> None:
    llm = MockLLM([main.keyword_judge] * 3)
    v_good = main.judge_pointwise(llm, main.QUESTION, main.REFERENCE, GOOD)
    v_invented = main.judge_pointwise(llm, main.QUESTION, main.REFERENCE, main.CASES[3]["answer"])
    v_long = main.judge_pointwise(llm, main.QUESTION, main.REFERENCE, main.CASES[4]["answer"])
    assert v_good.passed
    assert v_invented.correct and not v_invented.grounded  # the $10 voucher is not in the reference
    assert v_long.correct and not v_long.concise


def test_pairwise_is_consistent_for_a_fair_judge() -> None:
    llm = MockLLM([main.keyword_judge] * 2)
    assert main.judge_pairwise(llm, main.QUESTION, main.REFERENCE, GOOD, INCOMPLETE) == "A"
    # the second call really did swap the order
    second_prompt = llm.calls[1]["messages"][0]["content"]
    assert second_prompt.index(INCOMPLETE) < second_prompt.index(GOOD)


def test_pairwise_catches_position_bias() -> None:
    llm = MockLLM([main.position_biased_judge] * 2)
    assert main.judge_pairwise(llm, main.QUESTION, main.REFERENCE, GOOD, INCOMPLETE) == "inconsistent"


def test_pairwise_reports_unreadable_replies() -> None:
    llm = MockLLM(["no idea", "no idea"])
    assert main.judge_pairwise(llm, main.QUESTION, main.REFERENCE, GOOD, INCOMPLETE) == "error"


def test_agreement_and_kappa() -> None:
    human = [True, False, True, False]
    assert main.agreement(human, human) == 1.0
    assert main.cohens_kappa(human, human) == pytest.approx(1.0)
    # a judge that always says "fail" agrees half the time here, but kappa shows it is no better than chance
    always_fail = [False] * 4
    assert main.agreement(always_fail, human) == 0.5
    assert main.cohens_kappa(always_fail, human) == pytest.approx(0.0)


def test_demo_finds_exactly_one_disagreement() -> None:
    llm = MockLLM([main.keyword_judge] * len(main.CASES))
    judged = [main.judge_pointwise(llm, main.QUESTION, main.REFERENCE, c["answer"]).passed for c in main.CASES]
    human = [c["human"] for c in main.CASES]
    assert [c["id"] for c, j, h in zip(main.CASES, judged, human) if j != h] == ["c3"]
