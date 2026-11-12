"""Prompt chaining: each step gets only what it needs, and gates stop bad output. Offline, with MockLLM."""

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_three_steps_three_calls() -> None:
    llm = MockLLM(main.SCRIPT)
    result = main.run_chain(llm, main.CHANGELOG)
    assert len(llm.calls) == 3
    assert len(result.changes) == 3
    assert result.translation.startswith("Novedades")


def test_each_step_receives_only_the_previous_output() -> None:
    llm = MockLLM(main.SCRIPT)
    result = main.run_chain(llm, main.CHANGELOG)
    step2_input = llm.calls[1]["messages"][0]["content"]
    assert "refactor" not in step2_input and "- The reports page has a dark mode" in step2_input
    assert llm.calls[2]["messages"][0]["content"] == result.announcement


def test_gate_stops_the_chain_on_bad_json() -> None:
    llm = MockLLM(["Here are the changes: dark mode, budgets."])
    with pytest.raises(main.GateFailed, match="did not return JSON"):
        main.run_chain(llm, main.CHANGELOG)
    assert len(llm.calls) == 1  # steps 2 and 3 never ran, so no money was wasted


def test_gate_rejects_jargon_in_the_announcement() -> None:
    llm = MockLLM([main.SCRIPT[0], "We refactored the accounts service and bumped deps."])
    with pytest.raises(main.GateFailed, match="jargon"):
        main.run_chain(llm, main.CHANGELOG)
    assert len(llm.calls) == 2


def test_gate_rejects_long_announcement() -> None:
    with pytest.raises(main.GateFailed, match="limit"):
        main.gate_announcement("word " * (main.MAX_WORDS + 1))


def test_gate_changes_shape() -> None:
    assert main.gate_changes('["a", "b"]') == ["a", "b"]
    for bad in ("[]", '{"a": 1}', '["ok", ""]', '["ok", 3]'):
        with pytest.raises(main.GateFailed):
            main.gate_changes(bad)
