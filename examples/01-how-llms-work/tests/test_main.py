"""Statelessness and token growth, demonstrated offline with MockLLM."""

from types import SimpleNamespace as NS
from typing import Any

from common import AnthropicLLM, MockLLM, user
from common.testing import load_example

main = load_example(__file__)


def test_model_forgets_without_history() -> None:
    llm = MockLLM([main.remembers_name] * 2)
    assert "don't know" in main.ask_without_history(llm)
    # the second request really did not contain the first message
    assert all("Sam" not in m["content"] for m in llm.calls[1]["messages"])


def test_model_remembers_when_history_is_resent() -> None:
    llm = MockLLM([main.remembers_name] * 2)
    assert main.ask_with_history(llm) == "Your name is Sam."
    assert len(llm.calls[1]["messages"]) == 3  # user, assistant, user


def test_input_tokens_grow_every_turn() -> None:
    sizes = main.growing_conversation(MockLLM(main.SCRIPTED_ANSWERS), main.QUESTIONS)
    tokens = [t for _, t in sizes]
    assert tokens == sorted(tokens) and len(set(tokens)) == 3


def test_estimate_tokens() -> None:
    assert main.estimate_tokens("abcd" * 10) == 10
    assert main.estimate_tokens("") == 1


def test_count_tokens_uses_anthropic_api_when_available() -> None:
    seen: dict[str, Any] = {}

    def count_tokens(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return NS(input_tokens=42)

    client = NS(messages=NS(count_tokens=count_tokens))
    llm = AnthropicLLM("claude-opus-5-5", client=client)
    tokens, method = main.count_tokens(llm, [user("hi")], system="Be brief.")
    assert tokens == 42 and method.startswith("exact")
    assert seen == {"model": "claude-opus-5-5", "messages": [{"role": "user", "content": "hi"}], "system": "Be brief."}


def test_count_tokens_estimates_for_other_providers() -> None:
    tokens, method = main.count_tokens(MockLLM(), [user("x" * 40)])
    assert tokens == 10 and method.startswith("estimate")
