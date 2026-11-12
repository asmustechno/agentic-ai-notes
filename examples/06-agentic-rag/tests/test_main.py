"""Classic RAG vs agentic RAG over the same documents. Offline, with MockLLM."""

import json

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_retrieval_ranks_the_obvious_document_first() -> None:
    assert main.retrieve("Business plan price per month")[0][0] == "pricing.md"
    assert main.retrieve("how long are backups kept")[0][0] == "backups.md"
    assert main.retrieve("on-premises install") == []  # nothing passes the score threshold


def test_search_tool_returns_json_or_a_clear_not_found() -> None:
    hits = json.loads(main.search_docs("SSO single sign-on plan", top_k=1))
    assert hits[0]["id"] == "sso.md" and "Business plan only" in hits[0]["text"]
    assert main.search_docs("quantum teleportation").startswith("No relevant documents found")
    assert len(json.loads(main.search_docs("plan", top_k=99))) <= 5  # top_k is clamped


def test_classic_rag_misses_the_second_hop() -> None:
    llm = MockLLM(main.CLASSIC_SCRIPT)
    _, hits = main.classic_rag(llm, main.MULTI_HOP)
    assert hits[0] == "sso.md"
    assert "pricing.md" not in hits  # the price lives in a document the raw question doesn't match
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "<document id='sso.md'>" in prompt and prompt.endswith(f"Question: {main.MULTI_HOP}")
    assert llm.calls[0]["tools"] is None  # classic RAG gives the model no tools


def test_agent_does_two_hops_and_reads_both_results() -> None:
    llm = MockLLM(main.AGENT_SCRIPT[:3])
    agent = main.RagAgent(llm)
    answer = agent.run(main.MULTI_HOP)
    assert "$199" in answer and "[pricing.md]" in answer
    assert [t["name"] for t in llm.calls[0]["tools"]] == ["search_docs"]
    assert "Never answer from memory" in llm.calls[0]["system"]
    # the second search result (pricing.md) reached the model before it answered
    last_tool_msg = [m for m in llm.calls[2]["messages"] if m["role"] == "tool"][-1]
    assert json.loads(last_tool_msg["content"])[0]["id"] == "pricing.md"
    assert agent.log[:2] == [
        "step 1: search_docs('SSO single sign-on plan') -> ['sso.md']",
        "step 2: search_docs('Business plan price per month') -> ['pricing.md', 'sso.md', 'limits.md']",
    ]


def test_agent_says_not_found_after_a_rewrite() -> None:
    llm = MockLLM(main.AGENT_SCRIPT[3:6])
    agent = main.RagAgent(llm)
    answer = agent.run(main.NOT_FOUND)
    assert "couldn't find" in answer
    assert sum("-> nothing" in line for line in agent.log) == 2  # first query, then the rewritten one


def test_agent_skips_search_when_not_needed() -> None:
    llm = MockLLM(main.AGENT_SCRIPT[6:])
    agent = main.RagAgent(llm)
    agent.run(main.CHIT_CHAT)
    assert len(llm.calls) == 1 and agent.log == ["step 1: answer"]


def test_unknown_tool_is_reported_as_an_error() -> None:
    llm = MockLLM([MockLLM.tool_call("delete_docs", {}), "ok"])
    main.RagAgent(llm).run("hi")
    tool_msg = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"][0]
    assert tool_msg["is_error"] is True


def test_step_limit() -> None:
    llm = MockLLM([MockLLM.tool_call("search_docs", {"query": "plan"})] * 10)
    agent = main.RagAgent(llm, max_steps=3)
    assert "step limit" in agent.run("loop")
    assert len(llm.calls) == 3
