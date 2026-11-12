"""Test results drive the fixes. Offline, with MockLLM.

Every piece of code executed here is scripted in main.py or in this file and known to be safe.
"""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_first_attempt_fails_second_passes() -> None:
    llm = MockLLM(main.SCRIPT)
    result = main.solve_with_tests(llm, main.TASK)
    assert result.passed
    assert len(result.attempts) == 2 and len(llm.calls) == 2
    assert not result.attempts[0].run.passed
    assert "FAIL slugify('Hello, World!')" in result.attempts[0].run.output
    assert result.attempts[1].run.output.startswith("PASS")


def test_real_failure_output_is_sent_back_to_the_model() -> None:
    llm = MockLLM(main.SCRIPT)
    main.solve_with_tests(llm, main.TASK)
    second = llm.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert "def slugify" in second[1]["content"]  # the model sees its own code
    assert "expected 'hello-world', got 'hello,-world!'" in second[2]["content"]  # and the exact failure


def test_gives_up_after_max_attempts() -> None:
    llm = MockLLM([main.ATTEMPT_1] * 3)
    result = main.solve_with_tests(llm, main.TASK, max_attempts=3)
    assert not result.passed and len(llm.calls) == 3


def test_crash_is_reported_as_a_failure() -> None:
    run = main.run_tests("def slugify(title):\n    raise ValueError('boom')")
    assert not run.passed
    assert "raised ValueError: boom" in run.output


def test_syntax_error_is_reported() -> None:
    run = main.run_tests("def slugify(title) return title")
    assert not run.passed and "SyntaxError" in run.output


def test_infinite_loop_is_killed_by_the_timeout() -> None:
    run = main.run_tests("def slugify(title):\n    while True:\n        pass", timeout=2)
    assert not run.passed and run.output.startswith("TIMEOUT")


def test_extract_code() -> None:
    assert main.extract_code(main.ATTEMPT_2).startswith("import re")
    assert main.extract_code("Sure!\n```python\nx = 1\n```\nDone.") == "x = 1"
    assert main.extract_code("x = 1") == "x = 1"
