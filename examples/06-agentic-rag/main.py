"""Agentic RAG: retrieval is a tool, and the agent decides when, what and how often to search.

    python main.py                   # from this folder
    python 06-agentic-rag/main.py    # from examples/

Compares two designs on the same small document set:

  1. classic RAG: always retrieve the top 2 chunks for the raw question, then answer once;
  2. agentic RAG: the model gets a `search_docs` tool, rewrites queries, searches
     more than once for multi-hop questions, and says "not found" when it is.

The search engine is a tiny pure-Python vector index (hashed bag-of-words plus
cosine similarity), so everything runs offline. Real systems use an embedding
model and a vector database; see docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md.

Read alongside docs/06-rag-for-agents/06.4-agentic-rag.md and 06.1-rag-in-5-minutes.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- the knowledge base

DOCS: dict[str, str] = {
    "pricing.md": "Prices. Starter is free. Pro is $49 per month. Business is $199 per month. "
    "Prices exclude VAT and are billed monthly.",
    "sso.md": "Single sign-on (SSO). Staff can log in with Okta or Azure AD. "
    "SSO is available on the Business plan only.",
    "backups.md": "Backups. Every database is backed up daily. Backups are kept for 7 days on Starter, "
    "30 days on Pro and 90 days on Business.",
    "regions.md": "Data regions. Customer data is stored in Frankfurt or Virginia. "
    "You choose the region when you create a project, and it cannot be changed later.",
    "support.md": "Support. Email support answers within two business days. "
    "Live chat is open 09:00 to 17:00 UTC on weekdays for Pro and Business customers.",
    "security.md": "Security. All data is encrypted at rest. SSO sessions expire after 12 hours, "
    "and admins can force a logout from the dashboard.",
    "changelog.md": "Changelog, October 2026. New SSO login page. Faster database restores. Dark mode for the dashboard.",
    "limits.md": "API limits. Starter includes 10,000 API requests per month and Pro includes 1,000,000. "
    "Requests over the limit return HTTP 429 until the next month starts.",
}

# --------------------------------------------------------------------------- a tiny vector index (pure Python)

STOPWORDS = set("a an and are as at be by can do does for from how i in is it its my of on or so that the this "
                "to what when which who with you your".split())
DIM = 512


def tokenize(text: str) -> list[str]:
    """Lowercase words, minus stop words, with a crude plural strip ("costs" -> "cost")."""
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


def embed(text: str) -> list[float]:
    """Hashed bag-of-words, normalised to length 1. A stand-in for a real embedding model."""
    vec = [0.0] * DIM
    for tok in tokenize(text):
        vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


INDEX: dict[str, list[float]] = {doc_id: embed(text) for doc_id, text in DOCS.items()}  # built once, up front
MIN_SCORE = 0.2  # below this we treat a match as noise


def retrieve(query: str, k: int = 3, min_score: float = MIN_SCORE) -> list[tuple[str, float]]:
    """Top-k (doc_id, score) pairs scoring at least `min_score`, best first."""
    q = embed(query)
    scored = sorted(((doc_id, cosine(q, vec)) for doc_id, vec in INDEX.items()), key=lambda p: -p[1])
    return [(doc_id, round(score, 2)) for doc_id, score in scored[:k] if score >= min_score]


# --------------------------------------------------------------------------- 1. classic RAG (retrieve, then generate)

CLASSIC_SYSTEM = "Answer using only the documents provided. Cite document ids in [brackets]. If they do not contain the answer, say so."


def classic_rag(llm: LLM, question: str, k: int = 2) -> tuple[str, list[str]]:
    """One retrieval for the raw question, one model call. Returns (answer, retrieved doc ids)."""
    hits = [doc_id for doc_id, _ in retrieve(question, k, min_score=0.0)]  # always the top k, however weak
    context = "\n\n".join(f"<document id='{d}'>\n{DOCS[d]}\n</document>" for d in hits)
    reply = llm.chat([user(f"{context}\n\nQuestion: {question}")], system=CLASSIC_SYSTEM)
    return reply.text, hits


# --------------------------------------------------------------------------- 2. agentic RAG (retrieval as a tool)

SEARCH_SPEC: ToolSpec = {
    "name": "search_docs",
    "description": (
        "Search the Acme Cloud documentation. Returns up to top_k matching documents with their id, "
        "relevance score (0-1) and full text, or a 'no relevant documents' message. "
        "Write short keyword queries about one fact at a time, e.g. 'Business plan price'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keywords for one fact, e.g. 'SSO plan'."},
            "top_k": {"type": "integer", "description": "How many documents to return (1-5). Default 3."},
        },
        "required": ["query"],
    },
}


def search_docs(query: str, top_k: int = 3) -> str:
    """The tool the agent calls. Returns JSON the model can read."""
    hits = retrieve(query, max(1, min(int(top_k), 5)))
    if not hits:
        return f"No relevant documents found for: {query!r}"
    return json.dumps([{"id": d, "score": s, "text": DOCS[d]} for d, s in hits])


AGENT_SYSTEM = """You answer questions about Acme Cloud using its documentation.

- For any factual question about Acme Cloud, call search_docs before answering. Never answer from memory.
- Search for one fact at a time with short keyword queries. If a question needs two facts
  (for example "the plan that has X" and then "that plan's price"), search for the first, read the result,
  then search for the second.
- If a search returns nothing useful, rewrite the query once with different words (synonyms, product names).
- If you still find nothing, say "I couldn't find that in the Acme Cloud docs." Do not guess.
- Greetings and questions about what you can do need no search.
- Cite the document ids you used in [brackets]. Keep answers to one or two sentences."""


@dataclass
class RagAgent:
    llm: LLM
    max_steps: int = 6
    log: list[str] = field(default_factory=list)

    def run(self, question: str) -> str:
        messages: list[Message] = [user(question)]
        for step in range(1, self.max_steps + 1):
            reply = self.llm.chat(messages, system=AGENT_SYSTEM, tools=[SEARCH_SPEC])
            messages.append(reply.to_message())
            if not reply.tool_calls:
                self.log.append(f"step {step}: answer")
                return reply.text
            for call in reply.tool_calls:
                if call.name != "search_docs":
                    messages.append(tool_result(call.id, f"Unknown tool {call.name}", is_error=True))
                    continue
                result = search_docs(**call.arguments)
                found = [d["id"] for d in json.loads(result)] if result.startswith("[") else []
                self.log.append(f"step {step}: search_docs({call.arguments['query']!r}) -> {found or 'nothing'}")
                messages.append(tool_result(call.id, result))
        return "I could not finish within the step limit."


# --------------------------------------------------------------------------- the demo

MULTI_HOP = "How much does the plan with SSO cost?"
NOT_FOUND = "Can I install Acme Cloud on my own servers?"
CHIT_CHAT = "Hi! What can you help me with?"

CLASSIC_SCRIPT = [
    "SSO is available on the Business plan [sso.md], but the documents provided don't say what the Business plan costs.",
]
AGENT_SCRIPT = [
    # multi-hop: find the plan, then its price
    MockLLM.tool_call("search_docs", {"query": "SSO single sign-on plan"}),
    MockLLM.tool_call("search_docs", {"query": "Business plan price per month"}),
    "SSO is only on the Business plan [sso.md], which costs $199 per month, excluding VAT [pricing.md].",
    # not found: one search, one rewrite, then an honest answer
    MockLLM.tool_call("search_docs", {"query": "on-premises install"}),
    MockLLM.tool_call("search_docs", {"query": "self-hosted deployment own servers"}),
    "I couldn't find that in the Acme Cloud docs: they say nothing about running it on your own servers.",
    # no search needed
    "I can answer questions about Acme Cloud's plans, pricing, backups, data regions, support and API limits.",
]


def main() -> None:
    print(f"Q: {MULTI_HOP}\n")
    answer, hits = classic_rag(get_llm(mock_responses=CLASSIC_SCRIPT), MULTI_HOP)
    print(f"1) CLASSIC RAG  retrieved {hits} for the raw question")
    print(f"   {answer}\n")

    agent = RagAgent(get_llm(mock_responses=AGENT_SCRIPT))
    print("2) AGENTIC RAG")
    for question in (MULTI_HOP, NOT_FOUND, CHIT_CHAT):
        agent.log.clear()
        answer = agent.run(question)
        print(f"   Q: {question}")
        print("\n".join(f"      {line}" for line in agent.log))
        print(f"   A: {answer}\n")


if __name__ == "__main__":
    main()
