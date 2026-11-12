"""The reflection loop drafts, critiques and revises. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_draft_critique_revise_then_stop() -> None:
    llm = MockLLM(main.SCRIPT)
    result = main.reflect(llm, main.TASK)
    assert len(llm.calls) == 4  # draft, critique, revise, critique
    assert result.final.startswith("Version 2.3 fixes a problem")
    assert len(result.drafts) == 2 and len(result.critiques) == 2
    assert result.stopped_because == "critic found no issues"


def test_writer_and_critic_use_different_system_prompts() -> None:
    llm = MockLLM(main.SCRIPT)
    main.reflect(llm, main.TASK)
    assert llm.calls[0]["system"] == main.WRITER_SYSTEM
    assert llm.calls[1]["system"] == main.CRITIC_SYSTEM
    assert llm.calls[2]["system"] == main.WRITER_SYSTEM


def test_critique_is_fed_into_the_revision() -> None:
    llm = MockLLM(main.SCRIPT)
    main.reflect(llm, main.TASK)
    revise_prompt = llm.calls[2]["messages"][0]["content"]
    assert "race condition" in revise_prompt  # the old draft
    assert "Jargon" in revise_prompt  # the critique


def test_critic_sees_a_fresh_conversation() -> None:
    llm = MockLLM(main.SCRIPT)
    main.reflect(llm, main.TASK)
    assert len(llm.calls[1]["messages"]) == 1  # no writer history leaks into the critique


def test_stops_after_max_rounds_if_never_clean() -> None:
    llm = MockLLM(["draft"] + ["- still wrong", "revised"] * 5)
    result = main.reflect(llm, main.TASK, max_rounds=2)
    assert len(llm.calls) == 5  # draft + 2 x (critique, revise)
    assert result.stopped_because == "hit max_rounds=2"
    assert result.final == "revised"


def test_is_clean_is_strict() -> None:
    assert main.is_clean("NO ISSUES")
    assert main.is_clean(" no issues. ")
    assert not main.is_clean("No issues, but the second sentence is long.")
