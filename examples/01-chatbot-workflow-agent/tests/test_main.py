"""Chatbot, workflow and agent behave as described in chapter 1.2. Offline, with MockLLM."""

import pytest

from common import MockLLM, MockLLMExhausted
from common.testing import load_example

main = load_example(__file__)


def test_chatbot_makes_one_call_without_tools() -> None:
    llm = MockLLM(main.CHATBOT_SCRIPT)
    main.chatbot(llm, main.QUESTION)
    assert len(llm.calls) == 1
    assert llm.calls[0]["tools"] is None


def test_workflow_fetches_data_in_code_then_calls_model_once() -> None:
    llm = MockLLM(main.WORKFLOW_SCRIPT)
    main.workflow(llm, main.QUESTION)
    assert len(llm.calls) == 1
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "FS-998" in prompt and "Thursday" in prompt  # code put the data in the prompt
    assert llm.calls[0]["tools"] is None


def test_workflow_cannot_handle_a_case_it_was_not_written_for() -> None:
    llm = MockLLM([])
    assert main.workflow(llm, "Where is my order?") == "Please include your order number."
    assert llm.calls == []


def test_agent_chooses_tools_and_stops_when_done() -> None:
    llm = MockLLM(main.AGENT_SCRIPT)
    answer, trace = main.agent(llm, main.QUESTION)
    assert "Thursday" in answer
    assert [t.split("(")[0] for t in trace] == ["get_order", "get_tracking"]
    assert len(llm.calls) == 3
    # the tool result was sent back to the model on the next call
    assert llm.calls[1]["messages"][-1]["role"] == "tool"
    assert "FS-998" in llm.calls[1]["messages"][-1]["content"]


def test_agent_respects_max_steps() -> None:
    llm = MockLLM([MockLLM.tool_call("get_order", {"order_id": "1234"})] * 3)
    answer, trace = main.agent(llm, main.QUESTION, max_steps=3)
    assert answer.startswith("Sorry")
    assert len(trace) == 3
    with pytest.raises(MockLLMExhausted):
        llm.chat([])


def test_tools_return_readable_errors() -> None:
    assert "No order found" in main.get_order("0000")
    assert "No tracking found" in main.get_tracking("XX")
