"""Project 2 solution: a personal research assistant with search, citations and memory.

- A pluggable `search` tool. Offline by default: a small built-in corpus.
  Real option on Claude: Anthropic's server-side web search tool.
- Long-term memory in a JSON file (facts and preferences), recalled into the
  system prompt at the start of every session.
- Every claim cites a source id like [S1]; the code checks the ids and prints
  the source list, so the model can never invent a URL.

    python solution/main.py                                    # offline demo: two sessions
    python solution/main.py "What is prompt caching?"          # your question (use a real model)
    RESEARCH_SEARCH=anthropic LLM_PROVIDER=anthropic python solution/main.py "Latest MCP spec version?"

Read alongside docs/18-projects/18.2-project-2-research-assistant.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

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
        terms = set(_words(query))
        scored = []
        for doc in self.corpus:
            title, body = set(_words(doc.title)), set(_words(doc.snippet))
            score = 2 * len(terms & title) + len(terms & body)  # a title match counts double
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda pair: -pair[0])  # stable sort: ties keep corpus order
        return [doc for _, doc in scored[:k]]


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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, "memories": [asdict(m) for m in self.items]}, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic: a crash never leaves a half-written file

    def add(self, kind: str, text: str) -> str:
        kind, text = kind.strip().lower(), " ".join(text.split())
        if kind not in MEMORY_KINDS:
            raise ValueError(f"kind must be one of {MEMORY_KINDS}")
        if not 3 <= len(text) <= 200:
            raise ValueError("text must be 3 to 200 characters")
        for m in self.items:
            if m.text.lower() == text.lower():
                return f"Already remembered ({m.id})."
        number = max((int(m.id[1:]) for m in self.items), default=0) + 1
        self.items.append(Memory(f"m{number}", kind, text, date.today().isoformat()))
        self.items = self.items[-self.max_items :]  # forget the oldest beyond the cap
        self.save()
        return f"Saved {kind} m{number}."

    def forget(self, text: str) -> str:
        before = len(self.items)
        self.items = [m for m in self.items if text.lower() not in m.text.lower() and m.id != text]
        self.save()
        return f"Forgot {before - len(self.items)} item(s)."

    def recall(self, query: str = "", limit: int = 10) -> list[Memory]:
        """Up to `limit` memories: preferences first, then the ones that share most words with the query."""
        terms = set(_words(query))
        ranked = sorted(
            enumerate(self.items),
            key=lambda pair: (pair[1].kind != "preference", -len(terms & set(_words(pair[1].text))), -pair[0]),
        )
        return [m for _, m in ranked[:limit]]


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

    # ---- prompt and tools

    def system_prompt(self, question: str) -> str:
        memories = self.memory.recall(question)
        if not memories:
            return SYSTEM_PROMPT
        lines = "\n".join(f"- ({m.kind}) {m.text}" for m in memories)
        return f"{SYSTEM_PROMPT}\n\nWhat you remember about the user from earlier sessions:\n{lines}"

    def tools(self) -> list[ToolSpec]:
        return ([ANTHROPIC_WEB_SEARCH] if self.use_server_search else LOCAL_TOOLS) + MEMORY_TOOLS

    # ---- tools

    def _search(self, query: str) -> str:
        results = self.backend.search(query)
        if not results:
            return "No results. Try different keywords."
        out = []
        for r in results:
            sid = next((k for k, v in self.seen.items() if v.url == r.url), None) or f"S{len(self.seen) + 1}"
            self.seen[sid] = r
            out.append({"id": sid, "title": r.title, "url": r.url, "snippet": r.snippet})
        return json.dumps(out, indent=1)

    def run_tool(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        try:
            if name == "search" and not self.use_server_search:
                return self._search(args["query"]), False
            if name == "remember":
                return self.memory.add(args["kind"], args["text"]), False
            if name == "forget":
                return self.memory.forget(args["text"]), False
            return f"Error: unknown tool {name!r}", True
        except (KeyError, TypeError) as exc:
            return f"Error: missing or bad argument: {exc}", True
        except ValueError as exc:
            return f"Error: {exc}", True

    # ---- the loop

    def ask(self, question: str) -> Answer:
        system = self.system_prompt(question)
        self.messages.append(user(question))
        trace: list[str] = []
        for step in range(1, self.max_steps + 1):
            reply = self.llm.chat(self.messages, system=system, tools=self.tools())
            self.messages.append(reply.to_message())
            if _paused(reply):  # a long server-side search paused: send it back so it continues
                trace.append(f"step {step}: pause_turn, continuing")
                continue
            if not reply.tool_calls:
                trace.append(f"step {step}: answer")
                return self._finish(reply, trace)
            for call in reply.tool_calls:
                output, is_error = self.run_tool(call.name, call.arguments)
                trace.append(f"step {step}: {call.name}({json.dumps(call.arguments)}) -> {_shorten(output)}")
                self.messages.append(tool_result(call.id, output, is_error=is_error))
        return Answer("Sorry, I ran out of steps before finishing.", trace=trace + ["stopped: step limit"])

    def _finish(self, reply: LLMResponse, trace: list[str]) -> Answer:
        if self.use_server_search:  # Claude returns citations with each text block
            return Answer(reply.text, sources=_server_citations(reply), trace=trace)
        cited = list(dict.fromkeys(CITATION.findall(reply.text)))  # unique, in order
        sources, unsupported = [], []
        for sid in cited:
            if sid in self.seen:
                sources.append(Source(sid, self.seen[sid].title, self.seen[sid].url))
            else:
                unsupported.append(sid)
        return Answer(reply.text, sources, unsupported, trace)


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
    use_server = os.getenv("RESEARCH_SEARCH", "offline").lower() == "anthropic"
    if len(sys.argv) > 1:  # your own question, with a persistent memory file
        path = Path(os.getenv("MEMORY_FILE", Path.home() / ".agentic-ai-notes" / "research_memory.json"))
        bot = ResearchAssistant(get_llm(), MemoryStore(path), use_server_search=use_server)
        print(bot.ask(" ".join(sys.argv[1:])).render())
        print(f"\n(memory file: {path})")
        return

    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "memory.json"
        for n, (question, script) in enumerate([(SESSION_1, SESSION_1_SCRIPT), (SESSION_2, SESSION_2_SCRIPT)], 1):
            bot = ResearchAssistant(get_llm(mock_responses=script), MemoryStore(store_path), use_server_search=use_server)
            print(f"=== Session {n} ===")
            remembered = [m.text for m in bot.memory.recall(question)]
            print(f"Recalled from memory: {remembered or 'nothing yet'}")
            print(f"User: {question}")
            answer = bot.ask(question)
            print("\n".join("  " + t for t in answer.trace))
            print(answer.render() + "\n")
        print("Memory file after both sessions:")
        print(store_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
