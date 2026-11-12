"""The evaluator-optimizer loop: generator and evaluator are separate. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def run(gen_script: list, eval_script: list, max_rounds: int = 3):
    gen, ev = MockLLM(gen_script), MockLLM(eval_script)
    evaluator = main.Evaluator(ev)
    result = main.optimize(main.make_generator(gen), evaluator, max_rounds=max_rounds)
    return result, gen, ev, evaluator


def test_scripted_run_passes_on_round_three() -> None:
    result, gen, ev, evaluator = run(main.GENERATOR_SCRIPT, main.EVALUATOR_SCRIPT)
    assert result.passed and result.best == main.DRAFT_3
    assert len(result.rounds) == 3
    assert len(gen.calls) == 3
    assert len(ev.calls) == 2 == evaluator.model_calls  # draft 1 failed the hard checks, no model call


def test_hard_checks_catch_length_and_missing_order_id() -> None:
    problems = main.hard_checks(main.DRAFT_1)
    assert any("Too long" in p for p in problems)
    assert any(main.ORDER_ID in p for p in problems)
    assert main.hard_checks(main.DRAFT_3) == []


def test_feedback_reaches_the_generator() -> None:
    _, gen, _, _ = run(main.GENERATOR_SCRIPT, main.EVALUATOR_SCRIPT)
    second_prompt = gen.calls[1]["messages"][0]["content"]
    assert "Too long" in second_prompt and main.DRAFT_1 in second_prompt
    third_prompt = gen.calls[2]["messages"][0]["content"]
    assert "SORRY10" in third_prompt and "Criterion 3" in third_prompt


def test_generator_and_evaluator_get_different_prompts() -> None:
    _, gen, ev, _ = run(main.GENERATOR_SCRIPT, main.EVALUATOR_SCRIPT)
    assert gen.calls[0]["system"] == main.GENERATOR_SYSTEM
    assert ev.calls[0]["system"] == main.EVALUATOR_SYSTEM
    assert "Rubric:" in ev.calls[0]["messages"][0]["content"]


def test_returns_best_attempt_when_nothing_passes() -> None:
    fail = '{"pass": false, "score": %d, "feedback": "not yet"}'
    result, _, _, _ = run([main.DRAFT_2, main.DRAFT_3], [fail % 40, fail % 70], max_rounds=2)
    assert not result.passed
    assert result.best == main.DRAFT_3  # the higher score wins


def test_bad_evaluator_json_is_a_fail_not_a_pass() -> None:
    assert main.parse_verdict("Looks great to me!").passed is False
    assert main.parse_verdict('{"pass": "yes", "feedback": "ok"}').passed is False  # must be literally true
    v = main.parse_verdict('```json\n{"pass": true, "score": 90, "feedback": "ok"}\n```')
    assert v.passed and v.score == 90
