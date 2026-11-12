"""Vector memory: store memories as embeddings and recall them by similarity.

The embedder here is a tiny, pure-Python "bag of words + hashing" trick so the
example runs offline with no downloads. It only matches shared words. Real
systems use an embedding model (see OpenAIEmbedder below), which also matches
meaning: "food restrictions" finds "allergic to peanuts".

    python main.py                   # from this folder
    python 05-vector-memory/main.py  # from examples/

Read alongside docs/05-memory/05.3-vector-memory.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- embedders

STOPWORDS = set(
    "a an and are as at be by do does for from has have i in is it me my of on or our please "
    "remember that the their to user was we what when where which who with you your".split()  # "user" is in every memory
)


def tokenize(text: str) -> list[str]:
    """Lowercase words without stopwords, with a crude plural strip ("seats" -> "seat")."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if len(w) > 1 and w not in STOPWORDS]


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


@dataclass
class HashingEmbedder:
    """Bag-of-words feature hashing: each word adds ±1 to one of `dims` slots. Offline and deterministic.

    Teaching tool only: it knows nothing about meaning, synonyms or word order.
    """

    dims: int = 1024

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        for word in tokenize(text):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)  # stable across runs, unlike hash()
            vec[h % self.dims] += 1.0 if (h >> 64) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class OpenAIEmbedder:
    """A real embedding model through OpenAI's embeddings API. Needs OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL."""

    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.model = model or os.environ["OPENAI_EMBEDDING_MODEL"]  # e.g. a current model from the embeddings guide
        self.client = OpenAI()

    def embed(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity: 1.0 = same direction, 0.0 = nothing in common."""
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# --------------------------------------------------------------------------- the memory store


@dataclass
class Memory:
    id: int
    text: str
    vector: list[float]
    created_at: float
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorMemory:
    """A list of (text, vector) pairs with similarity search. Swap in a vector database at scale."""

    embedder: Embedder = field(default_factory=HashingEmbedder)
    items: list[Memory] = field(default_factory=list)

    def add(self, text: str, **meta: Any) -> Memory:
        item = Memory(len(self.items) + 1, text, self.embedder.embed(text), time.time(), meta)
        self.items.append(item)
        return item

    def search(self, query: str, k: int = 3, min_score: float = 0.2) -> list[tuple[float, Memory]]:
        """Top-k memories by cosine similarity, dropping weak matches below `min_score`."""
        q = self.embedder.embed(query)
        scored = sorted(((cosine(q, m.vector), m) for m in self.items), key=lambda s: s[0], reverse=True)
        return [(round(score, 2), m) for score, m in scored[:k] if score >= min_score]

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(m) for m in self.items]), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, embedder: Embedder | None = None) -> VectorMemory:
        items = [Memory(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
        return cls(embedder or HashingEmbedder(), items)


# --------------------------------------------------------------------------- memory as tools for an agent

REMEMBER_SPEC: ToolSpec = {
    "name": "remember",
    "description": "Save one durable fact about the user for future conversations. One fact per call, in plain words.",
    "input_schema": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]},
}
RECALL_SPEC: ToolSpec = {
    "name": "recall",
    "description": "Search saved facts about the user. Use short keyword queries, e.g. 'flight seat preference'.",
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}
INSTRUCTIONS = (
    "You are a travel assistant with long-term memory. When the user shares a lasting preference or fact, "
    "call remember. Before planning anything, call recall for facts that could matter. Be brief."
)


@dataclass
class MemoryAgent:
    model: LLM
    memory: VectorMemory
    max_steps: int = 5
    log: list[str] = field(default_factory=list)

    def tool(self, name: str, args: dict[str, Any]) -> str:
        if name == "remember":
            item = self.memory.add(args["fact"], source="user")
            return f"Saved memory #{item.id}."
        hits = self.memory.search(args["query"])
        return "\n".join(f"[{score}] {m.text}" for score, m in hits) or "No matching memories."

    def run(self, goal: str) -> str:
        messages: list[Message] = [user(goal)]
        for _ in range(self.max_steps):
            reply = self.model.chat(messages, system=INSTRUCTIONS, tools=[REMEMBER_SPEC, RECALL_SPEC])
            messages.append(reply.to_message())
            if not reply.tool_calls:
                return reply.text
            for call in reply.tool_calls:
                out = self.tool(call.name, call.arguments)
                self.log.append(f"{call.name}({call.arguments}) -> {out!r}")
                messages.append(tool_result(call.id, out))
        return "I could not finish within the step limit."


def answer_with_recalled(messages: list[Message]) -> str:
    """Scripted final reply that uses whatever the recall calls returned."""
    found = " ".join(m["content"] for m in messages if m["role"] == "tool")
    seat = "a window seat" if "window" in found else "any seat"
    snack = "a peanut-free snack" if "peanut" in found else "a snack"
    return f"I'll look for flights to Oslo with {seat}, and pack {snack} for Mia."


SESSION_1 = "Please remember: my daughter Mia is allergic to peanuts. Also, I always prefer window seats on flights."
SCRIPT_1: list[Any] = [
    MockLLM.tool_calls([
        ("remember", {"fact": "The user's daughter Mia is allergic to peanuts."}),
        ("remember", {"fact": "The user prefers window seats on flights."}),
    ]),
    "Got it. I'll remember both.",
]
SESSION_2 = "Find me a flight to Oslo next week, and suggest a snack for Mia for the trip."
SCRIPT_2: list[Any] = [
    MockLLM.tool_calls([("recall", {"query": "flight seat preference"}), ("recall", {"query": "Mia snack"})]),
    answer_with_recalled,
]


def main(path: Path | None = None) -> None:
    path = path or Path(tempfile.gettempdir()) / "agentic-ai-notes-vector-memory.json"

    print(f"SESSION 1: {SESSION_1}")
    agent = MemoryAgent(get_llm(mock_responses=SCRIPT_1), VectorMemory())
    agent.memory.add("The user lives in Manchester.", source="signup form")
    print(f"  answer: {agent.run(SESSION_1)}")
    print("  " + "\n  ".join(agent.log))
    agent.memory.save(path)
    print(f"  saved {len(agent.memory.items)} memories to {path.name}\n")

    print(f"SESSION 2 (new conversation, memory loaded from disk): {SESSION_2}")
    agent = MemoryAgent(get_llm(mock_responses=SCRIPT_2), VectorMemory.load(path))
    print(f"  answer: {agent.run(SESSION_2)}")
    print("  " + "\n  ".join(agent.log))

    print("\nWHERE BAG-OF-WORDS FAILS (scores against every memory)")
    show: Callable[[str], None] = lambda q: print(
        f"  {q!r}: " + ", ".join(f"#{m.id}={score}" for score, m in agent.memory.search(q, k=5, min_score=-1))
    )
    show("window seat")
    show("Does anyone in my family have food restrictions?")
    print("  The second query shares no words with 'allergic to peanuts', so it scores 0.0.\n"
          "  A good embedding model should score memory #2 highest: it compares meaning, not just words.")


if __name__ == "__main__":
    main()
