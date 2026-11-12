"""The subprocess runner enforces its limits. Every snippet here is harmless. Offline."""

from __future__ import annotations

import os
import time

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_runs_code_and_captures_stdout() -> None:
    result = main.run_python("print(6 * 7)")
    assert (result.stdout.strip(), result.exit_code, result.timed_out) == ("42", 0, False)


def test_errors_come_back_as_a_traceback() -> None:
    result = main.run_python("1 / 0")
    assert result.exit_code == 1
    assert "ZeroDivisionError" in result.stderr
    assert 'File "snippet.py"' in result.stderr  # no temporary path in the output


def test_infinite_loop_is_killed_by_the_timeout() -> None:
    start = time.monotonic()
    result = main.run_python("while True:\n    pass", timeout=1)
    assert result.timed_out and result.exit_code is None
    assert time.monotonic() - start < 10
    assert "timed out" in result.for_model()


def test_output_is_truncated() -> None:
    result = main.run_python("print('x' * 10_000)", max_output=100)
    assert result.stdout.startswith("x" * 100)
    assert "[output truncated: showing 100 of 10001 characters]" in result.stdout


def test_environment_variables_are_not_inherited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_API_KEY", "sk-should-not-leak")
    result = main.run_python("import os; print(os.environ.get('FAKE_API_KEY'))")
    assert result.stdout.strip() == "None"


def test_runs_in_an_empty_temporary_folder_that_is_removed() -> None:
    result = main.run_python("import os; print(os.getcwd()); print(sorted(os.listdir('.')))")
    cwd, listing = result.stdout.strip().splitlines()
    assert listing == "['snippet.py']"
    assert not os.path.exists(cwd)  # deleted after the run


def test_no_stdin() -> None:
    result = main.run_python("print(repr(input()))")
    assert result.exit_code == 1 and "EOFError" in result.stderr


@pytest.mark.skipif(os.name != "posix", reason="resource limits are POSIX-only")
def test_memory_limit_on_posix() -> None:
    result = main.run_python("x = bytearray(2 * 1024 * 1024 * 1024)", memory_mb=256)
    assert result.exit_code != 0 and "MemoryError" in result.stderr


def test_agent_fixes_its_own_bug() -> None:
    llm = MockLLM(main.SCRIPT)
    log: list[str] = []
    answer = main.run_agent(llm, main.GOAL, log=log)
    assert "7.77" in answer
    first = llm.calls[1]["messages"][-1]
    assert "NameError" in first["content"] and first["is_error"] is False  # a crash is an observation, not a tool failure
    assert "z-scores: {12: -0.57, 15: -0.18, 11: -0.7, 30: 1.75, 14: -0.31}" in llm.calls[2]["messages"][-1]["content"]


def test_spec_is_strict_friendly() -> None:
    schema = main.RUN_PYTHON_SPEC["input_schema"]
    assert schema["additionalProperties"] is False and schema["required"] == ["code"]
