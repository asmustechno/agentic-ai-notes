"""Project 2 starter: a personal research assistant with search, citations and memory.

Fill in every `# TODO`. The file runs as it is and tells you what is missing:

    python starter/main.py

Check your work with the same tests the solution passes (from examples/):

    PROJECT_TARGET=starter pytest 18-project-2-research-assistant          # macOS/Linux
    $env:PROJECT_TARGET="starter"; pytest 18-project-2-research-assistant  # Windows PowerShell

Guide: docs/18-projects/18.2-project-2-research-assistant.md
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date  # noqa: F401  (you will need it in MemoryStore.add)
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402,F401

# --------------------------------------------------------------------------- search: one interface, many backends


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchBackend(Protocol):
    """Anything with this method can be the agent's search engine (offline corpus, a web API, ...)."""

    def search(self, query: str, k: int = 3) -> list[SearchResult]: ...


CORPUS: list[SearchResult] = [
    SearchResult(
        "ReAct: Synergizing Reasoning and Acting in Language Models",
        "https://arxiv.org/abs/2210.03629",
        "Yao et al., 2022. The ReAct pattern interleaves reasoning traces with actions such as tool calls, "
        "so the model can plan, act, observe the result and update its plan.",
    ),
    SearchResult(
        "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "https://arxiv.org/abs/2303.11366",
        "Shinn et al., 2023. Agents write reflections on feedback from failed attempts and keep them in memory "
        "to do better on later attempts, without changing model weights.",
    ),
    SearchResult(
        "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "https://arxiv.org/abs/2201.11903",
        "Wei et al., 2022. Showing a model worked examples with intermediate reasoning steps improves its "
        "performance on multi-step arithmetic and reasoning tasks.",
    ),
    SearchResult(
        "Toolformer: Language Models Can Teach Themselves to Use Tools",
        "https://arxiv.org/abs/2302.04761",
        "Schick et al., 2023. A language model learns, in a self-supervised way, when to call external tools "
        "such as a calculator or a search engine and how to use the results.",
    ),
    SearchResult(
        "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "https://arxiv.org/abs/2005.11401",
        "Lewis et al., 2020. Combines a retriever over a document index with a generator, so answers are "
        "grounded in retrieved passages. The paper that named retrieval-augmented generation (RAG).",
    ),
    SearchResult(
        "Generative Agents: Interactive Simulacra of Human Behavior",
        "https://arxiv.org/abs/2304.03442",
        "Park et al., 2023. Simulated characters keep a memory stream of observations and retrieve memories "
        "by recency, importance and relevance before acting.",
    ),
    SearchResult(
        "Introducing the Model Context Protocol",
        "https://www.anthropic.com/news/model-context-protocol",
        "Anthropic, November 2024. Announces the Model Context Protocol (MCP), an open standard for "
        "connecting AI assistants to the systems where data lives, such as content repositories and tools.",
    ),
    SearchResult(
        "Model Context Protocol documentation",
        "https://modelcontextprotocol.io",
        "The official site for MCP: the specification, SDKs, and guides for building MCP servers "
        "that expose tools, resources and prompts to MCP clients.",
    ),
    SearchResult(
        "Building effective agents",
        "https://www.anthropic.com/engineering/building-effective-agents",
        "Anthropic, December 2024. Separates workflows (LLMs and tools on predefined code paths) from agents "
        "(LLMs that direct their own process and tool use) and recommends starting with the simplest solution.",
    ),
]

_STOPWORDS = set("a an and are as at be by does for from how i in is it of on or the to was what when which who why with".split())


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


class OfflineSearch:
    """Keyword search over a tiny built-in corpus. Deterministic, free and offline."""

    def __init__(self, corpus: list[SearchResult] | None = None) -> None:
        self.corpus = corpus if corpus is not None else CORPUS

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        """Return the top `k` results that share words with the query, best first; [] if none match.

        Score each document: 2 points per query word in the title, 1 per query word in the snippet.
        Use _words() to split text into lowercase words without stopwords.
        """
        # TODO (milestone 1)
        raise NotImplementedError("OfflineSearch.search (milestone 1)")


# Anthropic's server-side web search: Anthropic runs the searches, so there is no function to write.
# Pricing and newer versions: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
ANTHROPIC_WEB_SEARCH: ToolSpec = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


# --------------------------------------------------------------------------- long-term memory in a JSON file

MEMORY_KINDS = ("fact", "preference")


@dataclass
class Memory:
    id: str
    kind: str
    text: str
    created: str


class MemoryStore:
    """Facts and preferences that survive between sessions, stored as JSON on disk."""

    def __init__(self, path: Path | str, *, max_items: int = 50) -> None:
        self.path = Path(path)
        self.max_items = max_items
        self.items: list[Memory] = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [Memory(**m) for m in data.get("memories", [])]

    def save(self) -> None:
        """Write {"version": 1, "memories": [...]} to self.path (done for you)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, "memories": [asdict(m) for m in self.items]}, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic: a crash never leaves a half-written file

    def add(self, kind: str, text: str) -> str:
        """Save one memory and return "Saved <kind> m<N>." (or "Already remembered (m<N>)." for a duplicate).

        Raise ValueError if kind is not in MEMORY_KINDS or text is not 3-200 characters.
        Ids are m1, m2, ...; `created` is date.today().isoformat(); keep only the newest `max_items`; call save().
        """
        # TODO (milestone 2)
        raise NotImplementedError("MemoryStore.add (milestone 2)")

    def forget(self, text: str) -> str:
        """Remove memories whose text contains `text` (any case) or whose id equals it. Return "Forgot N item(s)."."""
        # TODO (milestone 2)
        raise NotImplementedError("MemoryStore.forget (milestone 2)")

    def recall(self, query: str = "", limit: int = 10) -> list[Memory]:
        """Up to `limit` memories: preferences first, then those sharing most words with the query, newest first on ties."""
        # TODO (milestone 2)
        raise NotImplementedError("MemoryStore.recall (milestone 2)")


# --------------------------------------------------------------------------- the assistant

SYSTEM_PROMPT = """You are a personal research assistant.

How to work:
- Use the search tool before answering any factual question. Search again with different words if results are poor.
- Cite every claim with the source id from the search results, like [S1]. Only cite ids you were given.
- If the sources don't answer the question, say so. Never invent facts or sources.
- When the user tells you a lasting preference or fact about themselves, save it with remember.
  Never save passwords, financial details or other sensitive data.
- Follow the user's saved preferences."""

LOCAL_TOOLS: list[ToolSpec] = [
    {
        "name": "search",
        "description": "Search for sources. Returns up to 3 results, each with a source id like S1, a title, a URL and a snippet.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A short keyword query, e.g. 'ReAct reasoning acting'."}},
            "required": ["query"],
        },
    },
]
MEMORY_TOOLS: list[ToolSpec] = [
    {
        "name": "remember",
        "description": "Save one lasting fact or preference about the user for future sessions, e.g. 'Prefers bullet points'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(MEMORY_KINDS)},
                "text": {"type": "string", "description": "One short sentence, under 200 characters."},
            },
            "required": ["kind", "text"],
        },
    },
    {
        "name": "forget",
        "description": "Delete saved memories that contain this text (or have this id), when the user asks you to forget something.",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    },
]

CITATION = re.compile(r"\[(S\d+)\]")


@dataclass
class Source:
    """A source the answer cites: the id the model used, plus the real title and URL."""

    id: str
    title: str
    url: str


@dataclass
class Answer:
    text: str
    sources: list[Source] = field(default_factory=list)  # the sources the answer cites
    unsupported: list[str] = field(default_factory=list)  # cited ids that no search returned
    trace: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [self.text]
        if self.sources:
            lines += ["", "Sources:"] + [f"  [{s.id}] {s.title} - {s.url}" for s in self.sources]
        if self.unsupported:
            lines.append(f"  (warning: cited ids with no source: {', '.join(self.unsupported)})")
        return "\n".join(lines)


class ResearchAssistant:
    """One session with the assistant. Create a new one per session; memory persists via the store."""

    def __init__(
        self,
        llm: LLM,
        memory: MemoryStore,
        search: SearchBackend | None = None,
        *,
        use_server_search: bool = False,
        max_steps: int = 6,
    ) -> None:
        if use_server_search and llm.provider != "anthropic":
            raise ValueError("Server-side web search needs LLM_PROVIDER=anthropic.")
        self.llm, self.memory, self.backend = llm, memory, search or OfflineSearch()
        self.use_server_search, self.max_steps = use_server_search, max_steps
        self.seen: dict[str, SearchResult] = {}  # source id -> result, for this session
        self.messages: list[Message] = []  # short-term memory: this session's conversation

    def system_prompt(self, question: str) -> str:
        """SYSTEM_PROMPT plus, if there are any, the recalled memories as lines like "- (preference) Prefers ...".

        Put them under the heading "What you remember about the user from earlier sessions:".
        """
        # TODO (milestone 3)
        raise NotImplementedError("ResearchAssistant.system_prompt (milestone 3)")

    def tools(self) -> list[ToolSpec]:
        return ([ANTHROPIC_WEB_SEARCH] if self.use_server_search else LOCAL_TOOLS) + MEMORY_TOOLS

    def _search(self, query: str) -> str:
        """Run the backend and return the results as a JSON list of {"id", "title", "url", "snippet"}.

        Give each new URL the next id (S1, S2, ...) and store it in self.seen; a URL seen before keeps its id.
        Return "No results. Try different keywords." when there are none.
        """
        # TODO (milestone 4)
        raise NotImplementedError("ResearchAssistant._search (milestone 4)")

    def run_tool(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Dispatch search / remember / forget. Return (output, is_error); never raise."""
        # TODO (milestone 4): catch KeyError, TypeError and ValueError and return ("Error: ...", True)
        raise NotImplementedError("ResearchAssistant.run_tool (milestone 4)")

    def ask(self, question: str) -> Answer:
        """The loop: append user(question), call the model with system_prompt(question) and tools(),
        run tool calls, stop on a plain answer (return self._finish(reply, trace)) or after max_steps
        (return an Answer whose text says it "ran out of steps"). If _paused(reply), just continue.
        """
        # TODO (milestone 5)
        raise NotImplementedError("ResearchAssistant.ask (milestone 5)")

    def _finish(self, reply: LLMResponse, trace: list[str]) -> Answer:
        """Build the Answer: find [S<n>] ids in reply.text (CITATION), map known ids to Source objects
        in order of first use, and list unknown ids in `unsupported`.
        With server search, use _server_citations(reply) instead.
        """
        # TODO (milestone 6)
        raise NotImplementedError("ResearchAssistant._finish (milestone 6)")


def _shorten(output: str) -> str:
    """A one-line summary of a tool result for the trace."""
    if output.startswith("["):  # search results: show the ids and titles only
        return ", ".join(f"{r['id']} {r['title'][:36].rstrip()}..." for r in json.loads(output))
    return output.splitlines()[0][:80] if output else ""


def _paused(reply: LLMResponse) -> bool:
    return reply.provider == "anthropic" and getattr(reply.raw, "stop_reason", None) == "pause_turn"


def _server_citations(reply: LLMResponse) -> list[Source]:
    """Collect the web sources Claude cited, from the raw Anthropic response's text blocks."""
    found: dict[str, Source] = {}
    for block in getattr(reply.raw, "content", None) or []:
        for c in getattr(block, "citations", None) or []:
            if getattr(c, "type", "") == "web_search_result_location" and c.url not in found:
                found[c.url] = Source(f"W{len(found) + 1}", c.title or c.url, c.url)
    return list(found.values())


# --------------------------------------------------------------------------- demo: two sessions, one memory file

SESSION_1 = "Hi! I'm a Python developer and I prefer short answers in bullet points. What is the ReAct pattern?"
SESSION_1_SCRIPT = [
    MockLLM.tool_calls(
        [
            ("remember", {"kind": "preference", "text": "Prefers short answers in bullet points."}),
            ("remember", {"kind": "fact", "text": "Is a Python developer."}),
            ("search", {"query": "ReAct pattern reasoning acting"}),
        ]
    ),
    "- ReAct interleaves reasoning with actions such as tool calls [S1].\n"
    "- The model plans, acts, observes the result and updates its plan [S1].",
]
SESSION_2 = "What is the Model Context Protocol?"
SESSION_2_SCRIPT = [
    MockLLM.tool_call("search", {"query": "Model Context Protocol"}),
    "- An open standard from Anthropic (November 2024) for connecting AI assistants to data and tools [S1].\n"
    "- MCP servers expose tools, resources and prompts to MCP clients [S2].",
]



def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "memory.json"
        try:
            for n, (question, script) in enumerate([(SESSION_1, SESSION_1_SCRIPT), (SESSION_2, SESSION_2_SCRIPT)], 1):
                bot = ResearchAssistant(get_llm(mock_responses=script), MemoryStore(store_path))
                print(f"=== Session {n} ===\nUser: {question}")
                answer = bot.ask(question)
                print("\n".join("  " + t for t in answer.trace))
                print(answer.render() + "\n")
        except NotImplementedError as exc:
            print(f"Not finished yet: {exc}. Open starter/main.py and look for '# TODO'.")


if __name__ == "__main__":
    main()
