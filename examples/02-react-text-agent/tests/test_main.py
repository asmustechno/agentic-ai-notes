"""The text-format ReAct agent parses actions, runs tools and stops. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_full_run_reaches_the_right_answer_in_four_steps() -> None:
    llm = MockLLM(main.SCRIPT)
    result = main.run_react(llm, main.QUESTION)
    assert result.answer is not None and result.answer.startswith("42 years")
    assert result.steps == 4
    actions = [line for line in result.trace if line.startswith("Action")]
    assert actions == [
        "Action 1: search[Eiffel Tower]",
        "Action 2: search[Empire State Building]",
        "Action 3: calculate[1931 - 1889]",
        "Action 4: finish[42 years. The Eiffel Tower was completed in 1889 and the Empire State Building opened in 1931.]",
    ]
    assert "Observation 3: 42" in result.trace


def test_observations_come_from_tools_not_from_the_model() -> None:
    llm = MockLLM(main.SCRIPT)
    main.run_react(llm, main.QUESTION)
    second_call = llm.calls[1]["messages"]
    # The invented "1887" observation was cut from the model's reply...
    assert "1887" not in second_call[1]["content"]
    # ...and the real observation, from our search tool, was sent instead.
    assert second_call[2] == {"role": "user", "content": "Observation: " + main.FAKE_ENCYCLOPEDIA["eiffel tower"]}


def test_no_native_tools_are_sent() -> None:
    llm = MockLLM(main.SCRIPT)
    main.run_react(llm, main.QUESTION)
    assert all(call["tools"] is None for call in llm.calls)
    assert "Action: <action>[<input>]" in llm.calls[0]["system"]


def test_parse_step() -> None:
    assert main.parse_step("Thought: hmm\nAction: search[Big Ben]") == ("hmm", ("search", "Big Ben"))
    assert main.parse_step("thought: x\n  action : CALCULATE[ 2 * 3 ]") == ("x", ("calculate", "2 * 3"))
    assert main.parse_step("I think the answer is 4.") == ("", None)


def test_missing_action_gets_format_help() -> None:
    llm = MockLLM(["The answer is probably 42.", "Thought: ok\nAction: finish[42]"])
    result = main.run_react(llm, "q")
    assert result.answer == "42"
    assert llm.calls[1]["messages"][-1]["content"] == "Observation: " + main.FORMAT_HELP


def test_unknown_action_is_reported_to_the_model() -> None:
    llm = MockLLM(["Thought: t\nAction: browse[example.com]", "Thought: t\nAction: finish[done]"])
    main.run_react(llm, "q")
    assert "Unknown action 'browse'" in llm.calls[1]["messages"][-1]["content"]


def test_step_limit() -> None:
    llm = MockLLM(["Thought: again\nAction: search[Big Ben]"] * 5)
    result = main.run_react(llm, "q", max_steps=3)
    assert result.answer is None and result.steps == 3 and len(llm.calls) == 3


def test_tools() -> None:
    assert "1931" in main.search("empire state building")
    assert main.search("Atlantis").startswith("No entry")
    assert main.calculate("1931 - 1889") == "42"
    assert main.calculate("__import__('os')").startswith("Error")
