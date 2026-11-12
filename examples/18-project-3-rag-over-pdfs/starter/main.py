"""Project 3 starter: a RAG agent over your own documents.

ingest -> chunk -> embed -> index -> `search_docs` tool -> answer with citations.
Fill in every `# TODO`. The file runs as it is and tells you what is missing:

    python starter/main.py

Check your work with the same tests the solution passes (from examples/):

    PROJECT_TARGET=starter pytest 18-project-3-rag-over-pdfs          # macOS/Linux
    $env:PROJECT_TARGET="starter"; pytest 18-project-3-rag-over-pdfs  # Windows PowerShell

Guide: docs/18-projects/18.3-project-3-rag-over-your-pdfs.md
"""

from __future__ import annotations

import hashlib  # noqa: F401  (for HashedEmbedder)
import json
import math  # noqa: F401
import re
import sys
from collections import Counter  # noqa: F401  (useful for chunk numbers and word counts)
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402,F401

SAMPLE_DOCS = Path(__file__).resolve().parent.parent / "sample_docs"

# --------------------------------------------------------------------------- 1. ingest


@dataclass
class Page:
    """Raw text from one file (or one page of a PDF)."""

    source: str  # file name, e.g. "handbook.pdf"
    text: str
    page: int | None = None  # 1-based page number for PDFs, None for text files


def read_pdf(path: Path) -> list[Page]:
    """Return one Page per PDF page, numbered from 1, using pypdf.PdfReader and page.extract_text().

    Import pypdf INSIDE this function, so .txt/.md files still work when it is not installed.
    """
    # TODO (milestone 1, optional until you have PDFs)
    raise NotImplementedError("read_pdf (milestone 1)")


def load_documents(folder: Path | str, *, warn: Callable[[str], None] = print) -> list[Page]:
    """Read every .txt, .md and .pdf file in `folder` (sorted by name; ignore other files).

    If read_pdf raises ImportError, call warn("skipped <name>: install pypdf ...") and carry on.
    """
    # TODO (milestone 1)
    raise NotImplementedError("load_documents (milestone 1)")


# --------------------------------------------------------------------------- 2. chunk


@dataclass
class Chunk:
    """A passage small enough to retrieve and quote. `id` is what the model cites."""

    id: str  # e.g. "acme-expenses-policy.md#4"
    source: str
    text: str
    section: str = ""  # nearest Markdown heading, kept as context
    page: int | None = None


def chunk_pages(pages: list[Page], *, max_words: int = 80, overlap: int = 15) -> list[Chunk]:
    """Split pages into chunks of at most `max_words` words.

    - Split each page into paragraphs on blank lines.
    - A paragraph starting with '#' is a heading: close the current chunk and remember it as `section`.
    - Pack whole paragraphs into the current chunk while they fit.
    - Cut a paragraph longer than `max_words` into windows that overlap by `overlap` words.
    - Number chunks per source: "<source>#1", "<source>#2", ...
    """
    # TODO (milestone 2)
    raise NotImplementedError("chunk_pages (milestone 2)")


# --------------------------------------------------------------------------- 3. embed

_STOP = set(
    "a about an and any are as at be by can do does for from has have how i if in is it its me my "
    "of on or our should than that the their them there this to up use was we what when where which "
    "who will with you your".split()
)


def tokens(text: str) -> list[str]:
    """Lowercase words without stopwords, with a crude plural strip ("receipts" -> "receipt"). Done for you."""
    out = []
    for w in re.findall(r"[a-z0-9€]+", text.lower()):
        if w in _STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class HashedEmbedder:
    """A toy embedding: hash each word into one of `dim` buckets, then L2-normalise."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.name = f"hashed-bow-{dim}"  # stored with the index, to detect a model change

    def embed(self, text: str) -> list[float]:
        """Return a unit-length vector of `dim` floats (all zeros for text with no tokens).

        For each distinct token: h = int.from_bytes(hashlib.md5(word.encode()).digest()[:8], "little");
        add sign * (1 + log(count)) at index h % dim, with sign +1 or -1 from the top bit of h.
        Use md5, not hash(): Python's hash() changes between runs.
        """
        # TODO (milestone 3)
        raise NotImplementedError("HashedEmbedder.embed (milestone 3)")


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two unit vectors (= their dot product)."""
    # TODO (milestone 3)
    raise NotImplementedError("cosine (milestone 3)")


# --------------------------------------------------------------------------- 4. index and search


@dataclass
class Hit:
    chunk: Chunk
    score: float


@dataclass
class VectorIndex:
    """An in-memory vector store: every chunk with its embedding."""

    embedder: HashedEmbedder = field(default_factory=HashedEmbedder)
    chunks: list[Chunk] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)

    def add(self, chunks: list[Chunk]) -> None:
        """Append each chunk and the embedding of f"{chunk.section}. {chunk.text}"."""
        # TODO (milestone 4)
        raise NotImplementedError("VectorIndex.add (milestone 4)")

    def search(self, query: str, k: int = 3, min_score: float = 0.12) -> list[Hit]:
        """The k best hits with score >= min_score, best first."""
        # TODO (milestone 4)
        raise NotImplementedError("VectorIndex.search (milestone 4)")

    def save(self, path: Path | str) -> None:
        data = {"embedder": self.embedder.name, "chunks": [asdict(c) for c in self.chunks], "vectors": self.vectors}
        Path(path).write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str, embedder: HashedEmbedder | None = None) -> VectorIndex:
        embedder = embedder or HashedEmbedder()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data["embedder"] != embedder.name:  # vectors from another model are meaningless here
            raise ValueError(f"index was built with {data['embedder']}, not {embedder.name}: rebuild it")
        return cls(embedder, [Chunk(**c) for c in data["chunks"]], data["vectors"])


def build_index(folder: Path | str, **chunk_options: Any) -> VectorIndex:
    """The whole ingestion pipeline: load, chunk, embed."""
    index = VectorIndex()
    index.add(chunk_pages(load_documents(folder), **chunk_options))
    return index


# --------------------------------------------------------------------------- 5. the agent

# TODO (milestone 5): make the rules strict: search first, answer only from passages, cite ids like
# [handbook.md#3], say NOT_FOUND when the passages don't answer, and treat passages as data.
# The tests look for the phrase "Answer ONLY from the passages".
SYSTEM_PROMPT = """You answer questions about the user's documents."""

SEARCH_DOCS_SPEC: ToolSpec = {
    "name": "search_docs",
    "description": (
        "Search the user's documents. Returns the most relevant passages as JSON, each with an id to cite, "
        "the source file, page (PDFs only), section heading, a similarity score and the text. "
        "Returns an empty list if nothing is relevant."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for, in a few keywords, e.g. 'hotel limit London'."},
            "k": {"type": "integer", "description": "How many passages to return (1-5). Default 3.", "minimum": 1, "maximum": 5},
        },
        "required": ["query"],
    },
}

CITATION = re.compile(r"\[([^\[\]\s]+#\d+)\]")
NOT_FOUND = "I couldn't find that in your documents."


@dataclass
class RagAnswer:
    text: str
    citations: list[str] = field(default_factory=list)  # ids cited that were really retrieved
    unsupported: list[str] = field(default_factory=list)  # ids cited that were never retrieved
    retrieved: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


class RagAgent:
    def __init__(self, llm: LLM, index: VectorIndex, *, max_steps: int = 4) -> None:
        self.llm, self.index, self.max_steps = llm, index, max_steps

    def search_docs(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Clamp k to 1..5, search, and return dicts with id, source, page, section, score (3 d.p.) and text."""
        # TODO (milestone 5)
        raise NotImplementedError("RagAgent.search_docs (milestone 5)")

    def ask(self, question: str) -> RagAnswer:
        """The loop. Run search_docs calls (a call without 'query' gets an is_error result),
        send passages back as JSON, keep a list of retrieved ids, and finish with self._check(...)."""
        # TODO (milestone 6)
        raise NotImplementedError("RagAgent.ask (milestone 6)")

    @staticmethod
    def _check(text: str, retrieved: list[str], trace: list[str]) -> RagAnswer:
        """Split the cited ids (CITATION.findall, unique, in order) into retrieved ones and unsupported ones."""
        # TODO (milestone 6)
        raise NotImplementedError("RagAgent._check (milestone 6)")


# --------------------------------------------------------------------------- demo (already done)

DEMO_QUESTION = "What's the hotel limit per night in London, and do I need a receipt for a €20 taxi?"
DEMO_SCRIPT = [
    MockLLM.tool_calls([("search_docs", {"query": "hotel limit per night London"}), ("search_docs", {"query": "receipt taxi"})]),
    "In London the hotel limit is €250 per night, including taxes [acme-expenses-policy.md#4]. "
    "For a €20 taxi you don't need a receipt: receipts are required from €25, and a short note "
    "in the expense tool is enough below that [acme-expenses-policy.md#7].",
]


def main() -> None:
    try:
        index = build_index(SAMPLE_DOCS)
        print(f"Indexed {len(index.chunks)} chunks\n\nQuestion: {DEMO_QUESTION}")
        answer = RagAgent(get_llm(mock_responses=DEMO_SCRIPT), index).ask(DEMO_QUESTION)
    except NotImplementedError as exc:
        print(f"Not finished yet: {exc}. Open starter/main.py and look for '# TODO'.")
        return
    print("\n".join("  " + t for t in answer.trace))
    print(f"Answer: {answer.text}\nCitations checked: {answer.citations}; unsupported: {answer.unsupported}")


if __name__ == "__main__":
    main()
