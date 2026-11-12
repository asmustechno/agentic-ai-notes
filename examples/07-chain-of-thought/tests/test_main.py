"""Chain-of-thought prompting: the right instructions go out, and only the answer comes back to the user."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_cot_prompt_asks_for_tags_and_answer_is_extracted() -> None:
    llm = MockLLM(main.SCRIPT[1:])
    result = main.ask(llm, main.QUESTION, chain_of_thought=True)
    assert "<thinking>" in llm.calls[0]["system"] and "<answer>" in llm.calls[0]["system"]
    assert result.answer == "9"
    assert "23 - 20 = 3" in result.reasoning


def test_direct_prompt_has_no_reasoning() -> None:
    llm = MockLLM(["27"])
    result = main.ask(llm, main.QUESTION, chain_of_thought=False)
    assert llm.calls[0]["system"] == main.DIRECT_SYSTEM
    assert (result.answer, result.reasoning) == ("27", "")


def test_reasoning_costs_output_tokens() -> None:
    llm = MockLLM(main.SCRIPT)
    direct = main.ask(llm, main.QUESTION, chain_of_thought=False)
    cot = main.ask(llm, main.QUESTION, chain_of_thought=True)
    assert cot.output_tokens > 10 * direct.output_tokens


def test_extract_handles_missing_tags() -> None:
    assert main.extract("<thinking>hmm</thinking> The answer is 9.") == ("The answer is 9.", "hmm")
    assert main.extract("9") == ("9", "")
    assert main.extract("<answer> 9 </answer>") == ("9", "")
