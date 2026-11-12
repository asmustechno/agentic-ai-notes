"""Acceptance tests for Project 2. Offline, with MockLLM and a temporary memory file.

By default they test solution/main.py. Set PROJECT_TARGET=starter to test your own work.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace as NS

import pytest

from common import LLM, LLMResponse, MockLLM


def load(target: str | None = None) -> ModuleType:
    """Import <project>/<target>/main.py under a unique module name."""
    target = target or os.getenv("PROJECT_TARGET", "solution")
    path = Path(__file__).resolve().parent.parent / target / "main.py"
    name = f"p18_2_research_{target}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader, f"cannot load {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


app = load()


# --------------------------------------------------------------------------- search


def test_offline_search_ranks_title_matches_first() -> None:
    results = app.OfflineSearch().search("ReAct reasoning acting")
    assert results[0].url == "https://arxiv.org/abs/2210.03629"
    assert len(results) <= 3
    assert app.OfflineSearch().search("zzzz qqqq") == []


def test_search_backend_is_pluggable(tmp_path: Path) -> None:
    class OneResult:
        def search(self, query: str, k: int = 3) -> list:
            return [app.SearchResult("Custom", "https://example.com/custom", f"about {query}")]

    llm = MockLLM([MockLLM.tool_call("search", {"query": "x"}), "It is custom [S1]."])
    answer = app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json"), OneResult()).ask("q")
    assert [s.url for s in answer.sources] == ["https://example.com/custom"]


# --------------------------------------------------------------------------- memory


def test_memory_persists_dedupes_and_validates(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    store = app.MemoryStore(path)
    assert "Saved" in store.add("preference", "Prefers metric units.")
    assert "Already" in store.add("preference", "prefers metric   units.")
    with pytest.raises(ValueError):
        store.add("secret", "my password is hunter2")
    reloaded = app.MemoryStore(path)  # a new session reads the same file
    assert [(m.kind, m.text) for m in reloaded.items] == [("preference", "Prefers metric units.")]
    assert json.loads(path.read_text(encoding="utf-8"))["memories"][0]["id"] == "m1"


def test_memory_forget_cap_and_recall_order(tmp_path: Path) -> None:
    store = app.MemoryStore(tmp_path / "m.json", max_items=3)
    for text in ["Works at a bank.", "Lives in Lyon.", "Has a cat called Mo."]:
        store.add("fact", text)
    store.add("preference", "Prefers bullet points.")
    assert len(store.items) == 3 and store.items[0].text == "Lives in Lyon."  # oldest dropped
    recalled = store.recall("what's the weather in Lyon")
    assert recalled[0].kind == "preference" and recalled[1].text == "Lives in Lyon."
    assert "1" in store.forget("cat")
    assert all("cat" not in m.text for m in app.MemoryStore(tmp_path / "m.json").items)


def test_second_session_recalls_memories_into_the_system_prompt(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    llm1 = MockLLM(app.SESSION_1_SCRIPT)
    app.ResearchAssistant(llm1, app.MemoryStore(path)).ask(app.SESSION_1)
    assert "Prefers short answers" not in llm1.calls[0]["system"]  # nothing known yet

    llm2 = MockLLM(app.SESSION_2_SCRIPT)
    app.ResearchAssistant(llm2, app.MemoryStore(path)).ask(app.SESSION_2)
    assert "(preference) Prefers short answers in bullet points." in llm2.calls[0]["system"]
    assert "(fact) Is a Python developer." in llm2.calls[0]["system"]


# --------------------------------------------------------------------------- citations


def test_answers_cite_real_sources_and_flag_invented_ids(tmp_path: Path) -> None:
    llm = MockLLM([MockLLM.tool_call("search", {"query": "ReAct"}), "ReAct mixes thinking and acting [S1]. Also [S9]."])
    answer = app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json")).ask("What is ReAct?")
    assert [s.id for s in answer.sources] == ["S1"]
    assert answer.sources[0].url == "https://arxiv.org/abs/2210.03629"
    assert answer.unsupported == ["S9"]
    rendered = answer.render()
    assert "Sources:" in rendered and "https://arxiv.org/abs/2210.03629" in rendered and "S9" in rendered


def test_search_results_reach_the_model_with_ids(tmp_path: Path) -> None:
    llm = MockLLM(app.SESSION_2_SCRIPT)
    app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json")).ask(app.SESSION_2)
    results = json.loads(llm.calls[1]["messages"][-1]["content"])
    assert [r["id"] for r in results][:2] == ["S1", "S2"]
    assert {"id", "title", "url", "snippet"} <= set(results[0])


def test_the_same_url_keeps_the_same_id(tmp_path: Path) -> None:
    llm = MockLLM([MockLLM.tool_call("search", {"query": "ReAct"}), MockLLM.tool_call("search", {"query": "ReAct reasoning"}), "ok"])
    bot = app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json"))
    bot.ask("q")
    react_ids = [sid for sid, r in bot.seen.items() if "2210.03629" in r.url]
    assert react_ids == ["S1"]


# --------------------------------------------------------------------------- tools and the loop


def test_bad_tool_calls_become_error_results(tmp_path: Path) -> None:
    llm = MockLLM([MockLLM.tool_call("remember", {"kind": "password", "text": "hunter2!"}), "Not saved."])
    app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json")).ask("Remember my password hunter2!")
    last = llm.calls[1]["messages"][-1]
    assert last["is_error"] is True and last["content"].startswith("Error")


def test_step_limit(tmp_path: Path) -> None:
    llm = MockLLM([MockLLM.tool_call("search", {"query": "x"})] * 5)
    answer = app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json"), max_steps=2).ask("q")
    assert "ran out of steps" in answer.text and len(llm.calls) == 2


def test_local_tools_by_default_server_search_only_on_anthropic(tmp_path: Path) -> None:
    bot = app.ResearchAssistant(MockLLM(), app.MemoryStore(tmp_path / "m.json"))
    assert [t["name"] for t in bot.tools()] == ["search", "remember", "forget"]
    with pytest.raises(ValueError):
        app.ResearchAssistant(MockLLM(), app.MemoryStore(tmp_path / "m.json"), use_server_search=True)


class FakeClaude(LLM):
    """Returns canned Anthropic-shaped replies, to test server-side search handling offline."""

    provider = "anthropic"

    def __init__(self, replies: list[LLMResponse]) -> None:
        self.replies, self.calls = replies, []

    def chat(self, messages, *, system=None, tools=None, max_tokens=16000) -> LLMResponse:  # noqa: ANN001
        self.calls.append({"tools": tools})
        return self.replies.pop(0)


def test_server_search_uses_claude_citations_and_handles_pause_turn(tmp_path: Path) -> None:
    paused = LLMResponse(stop_reason="other", provider="anthropic", raw=NS(stop_reason="pause_turn", content=[]))
    cite = NS(type="web_search_result_location", url="https://modelcontextprotocol.io", title="MCP", cited_text="...")
    final = LLMResponse(
        text="MCP is an open protocol.",
        provider="anthropic",
        raw=NS(stop_reason="end_turn", content=[NS(type="text", text="MCP is an open protocol.", citations=[cite])]),
    )
    llm = FakeClaude([paused, final])
    answer = app.ResearchAssistant(llm, app.MemoryStore(tmp_path / "m.json"), use_server_search=True).ask("What is MCP?")
    assert len(llm.calls) == 2  # the paused turn was sent back
    assert llm.calls[0]["tools"][0]["type"] == "web_search_20260209"
    assert [(s.id, s.url) for s in answer.sources] == [("W1", "https://modelcontextprotocol.io")]
