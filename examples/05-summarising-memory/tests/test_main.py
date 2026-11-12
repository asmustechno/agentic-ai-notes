"""Trimming vs summarising short-term memory. Offline, with MockLLM."""

from common import MockLLM, tool_result, user
from common.llm import ToolCall
from common.testing import load_example

main = load_example(__file__)


def mock() -> MockLLM:
    return MockLLM([main.fake_model] * 40)


def test_trimming_stays_in_budget_but_forgets_early_facts() -> None:
    llm = mock()
    bot = main.run("trim", llm)
    assert any("trimmed" in line for line in bot.memory.log)
    last = llm.calls[-1]
    assert main.estimate_tokens(last["messages"], last["system"]) <= bot.memory.max_tokens
    sent = last["system"] + " ".join(m["content"] for m in last["messages"])
    assert "900 euros" not in sent  # the budget fell off the end of the window


def test_summarising_keeps_early_facts_in_the_system_prompt() -> None:
    llm = mock()
    bot = main.run("summarise", llm)
    last_chat = llm.calls[-1]
    assert "<conversation_summary>" in last_chat["system"]
    assert "900 euros" in last_chat["system"] and "vegetarian" in last_chat["system"]
    assert main.estimate_tokens(last_chat["messages"], last_chat["system"]) <= bot.memory.max_tokens


def test_summary_request_uses_its_own_prompt_and_includes_the_earlier_summary() -> None:
    llm = mock()
    main.run("summarise", llm)
    summary_calls = [c for c in llm.calls if c["system"] == main.SUMMARISER_SYSTEM]
    assert len(summary_calls) >= 2
    assert "Earlier summary:" in summary_calls[-1]["messages"][0]["content"]  # summaries are rolled forward


def test_recent_turns_are_kept_word_for_word() -> None:
    bot = main.run("summarise", mock())
    kept = [m["content"] for m in bot.memory.messages if m["role"] == "user"]
    assert kept[-1] == main.CONVERSATION[-1][0]
    assert bot.memory.messages[0]["role"] == "user"  # history always starts on a user turn


def test_safe_cut_never_splits_a_tool_call_from_its_result() -> None:
    call = ToolCall(id="c1", name="weather", arguments={})
    msgs = [
        user("q1"), {"role": "assistant", "content": "", "tool_calls": [call]}, tool_result("c1", "sunny"),
        {"role": "assistant", "content": "It's sunny.", "tool_calls": []},
        user("q2"), {"role": "assistant", "content": "a2", "tool_calls": []},
    ]
    # Asking to keep 3 messages would start the tail on a tool result; the cut moves back to a user turn.
    assert main.safe_cut(msgs, keep_recent=3) == 0
    assert main.safe_cut(msgs, keep_recent=2) == 4


def test_no_summary_call_while_under_budget() -> None:
    llm = mock()
    memory = main.SummarisingMemory(llm, max_tokens=10_000)
    bot = main.ChatBot(llm, memory)
    bot.send("Hello")
    assert len(llm.calls) == 1 and memory.summary == ""
