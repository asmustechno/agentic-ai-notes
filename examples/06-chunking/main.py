"""Compare five ways to chunk the same document, and measure which one retrieval likes best.

    python main.py                 # from this folder
    python 06-chunking/main.py     # from examples/

Strategies: fixed-size with overlap, sentence packing, semantic breaks,
by headings, and parent-child. For each one we index the chunks, ask the
same questions, and check whether the top-ranked chunk contains the answer.

The "embedding" here is a tiny hashed bag-of-words written in pure Python, so
the example runs offline with no packages. Real systems use an embedding
model (see docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md).

Read alongside docs/06-rag-for-agents/06.3-chunking-strategies.md.
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable (kept for consistency)

# --------------------------------------------------------------------------- the document

HANDBOOK = """\
# Acme Cloud handbook

Acme Cloud hosts web apps and databases for small teams. This handbook covers plans, backups and support.

## Plans

### Starter plan

The Starter plan is free. It includes one project and 10,000 API requests per month. Backups are kept for 7 days. Support is by email only.

### Pro plan

The Pro plan costs $49 per month. It includes ten projects and 1,000,000 API requests per month. Backups are kept for 30 days. Pro customers can open live chat during business hours.

## Backups

Every database is backed up once a day at 02:00 UTC. You can restore a backup from the dashboard in a few clicks. A restore replaces the current data, so export anything you need first. Restores usually finish within ten minutes.

## Support

Email support answers within two business days. Live chat runs from 09:00 to 17:00 UTC, Monday to Friday. Urgent outages are posted on the status page at status.acme.example.

## Security

All data is encrypted at rest with AES-256. Staff can only access customer data after the customer grants a time-limited support token. We rotate encryption keys every 90 days.
"""

# Each question comes with a short phrase that the right chunk must contain.
QUESTIONS: list[tuple[str, str]] = [
    ("How long are backups kept on the Pro plan?", "Backups are kept for 30 days"),
    ("How many API requests does the Starter plan include?", "10,000 API requests"),
    ("What happens to my current data when I restore a backup?", "A restore replaces the current data"),
    ("What are the live chat support hours?", "09:00 to 17:00 UTC"),
    ("How often are encryption keys rotated?", "every 90 days"),
    ("How much does the Pro plan cost?", "$49 per month"),
]

# --------------------------------------------------------------------------- a toy embedding (pure Python)

STOPWORDS = set("a an and are as at be by can do does for from how i in is it its my of on or so the to what when"
                " with you your".split())
DIM = 512


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers, without stop words."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


def embed(text: str) -> list[float]:
    """Hashed bag-of-words: each word adds 1 to one of DIM buckets, then we normalise to length 1.

    We use hashlib, not hash(): Python's hash() of a string changes between runs.
    """
    vec = [0.0] * DIM
    for tok in tokenize(text):
        vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Our vectors already have length 1, so it is just the dot product."""
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------- chunks


@dataclass
class Chunk:
    text: str  # what we embed and search
    context: str = ""  # what we hand to the model if this chunk wins (parent-child returns the parent)

    def __post_init__(self) -> None:
        self.context = self.context or self.text


def split_sentences(text: str) -> list[str]:
    """A simple sentence splitter: break after . ! or ? followed by a space."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def fixed_size(doc: str, size: int = 40, overlap: int = 10) -> list[Chunk]:
    """Windows of `size` words; each window starts `size - overlap` words after the last."""
    words = doc.split()
    step = size - overlap
    return [Chunk(" ".join(words[i : i + size])) for i in range(0, max(len(words) - overlap, 1), step)]


def _body_sentences(doc: str) -> list[str]:
    """All sentences, ignoring heading lines."""
    body = " ".join(line for line in doc.splitlines() if line.strip() and not line.startswith("#"))
    return split_sentences(body)


def sentence_packed(doc: str, max_words: int = 40) -> list[Chunk]:
    """Whole sentences, packed together until the next one would exceed `max_words`."""
    chunks: list[Chunk] = []
    current: list[str] = []
    for sentence in _body_sentences(doc):
        if current and len(" ".join(current + [sentence]).split()) > max_words:
            chunks.append(Chunk(" ".join(current)))
            current = []
        current.append(sentence)
    if current:
        chunks.append(Chunk(" ".join(current)))
    return chunks


def semantic(doc: str, threshold: float = 0.1, min_words: int = 15) -> list[Chunk]:
    """Start a new chunk where two neighbouring sentences are not similar (a "topic shift").

    `min_words` stops it from making tiny chunks: a real embedding model sees more
    similarity between neighbouring sentences than our toy one does.
    """
    sentences = _body_sentences(doc)
    chunks: list[Chunk] = []
    current = [sentences[0]]
    for prev, sentence in zip(sentences, sentences[1:]):
        long_enough = len(" ".join(current).split()) >= min_words
        if long_enough and cosine(embed(prev), embed(sentence)) < threshold:
            chunks.append(Chunk(" ".join(current)))
            current = []
        current.append(sentence)
    chunks.append(Chunk(" ".join(current)))
    return chunks


def _sections(doc: str) -> list[tuple[str, str]]:
    """Split markdown into (heading path, body) pairs, e.g. ("Plans > Pro plan", "The Pro plan costs ...")."""
    path: list[str] = []
    sections: list[tuple[str, str]] = []
    body: list[str] = []

    def flush() -> None:
        if body:
            sections.append((" > ".join(path[1:]) or path[0], " ".join(body)))
            body.clear()

    for line in doc.splitlines():
        m = re.match(r"^(#+)\s+(.*)", line)
        if m:
            flush()
            level = len(m.group(1))
            path[:] = path[: level - 1] + [m.group(2).strip()]
        elif line.strip():
            body.append(line.strip())
    flush()
    return sections


def by_headings(doc: str) -> list[Chunk]:
    """One chunk per section, with its heading path written at the top."""
    return [Chunk(f"{heading}: {body}") for heading, body in _sections(doc)]


def parent_child(doc: str) -> list[Chunk]:
    """Search small children (one sentence + its heading), but return the whole parent section."""
    chunks: list[Chunk] = []
    for heading, body in _sections(doc):
        parent = f"{heading}: {body}"
        chunks += [Chunk(text=f"{heading}: {sentence}", context=parent) for sentence in split_sentences(body)]
    return chunks


STRATEGIES: dict[str, Callable[[str], list[Chunk]]] = {
    "fixed-size (40 words, 10 overlap)": fixed_size,
    "sentence-packed (<= 40 words)": sentence_packed,
    "semantic (break on topic shift)": semantic,
    "by headings": by_headings,
    "parent-child": parent_child,
}

# --------------------------------------------------------------------------- retrieval + scoring


def search(chunks: list[Chunk], query: str, k: int = 1) -> list[tuple[float, Chunk]]:
    """Rank chunks by cosine similarity to the query and return the top k."""
    q = embed(query)
    scored = sorted(((cosine(q, embed(c.text)), c) for c in chunks), key=lambda pair: -pair[0])
    return scored[:k]


@dataclass
class Report:
    name: str
    n_chunks: int
    avg_words: float
    hits: int
    total: int
    misses: list[str]


def evaluate(name: str, chunker: Callable[[str], list[Chunk]], doc: str = HANDBOOK) -> Report:
    """Index the document with one strategy and count top-1 hits (the answer is in the returned context)."""
    chunks = chunker(doc)
    hits, misses = 0, []
    for question, answer in QUESTIONS:
        _, best = search(chunks, question)[0]
        if answer in best.context:
            hits += 1
        else:
            misses.append(question)
    avg = sum(len(c.context.split()) for c in chunks) / len(chunks)
    return Report(name, len(chunks), avg, hits, len(QUESTIONS), misses)


def main() -> None:
    print(f"{'Strategy':36} {'chunks':>6} {'avg words':>9} {'top-1 hits':>10}")
    reports = [evaluate(name, fn) for name, fn in STRATEGIES.items()]
    for r in reports:
        print(f"{r.name:36} {r.n_chunks:>6} {r.avg_words:>9.1f} {r.hits:>6}/{r.total}")
    print("\nMisses:")
    for r in reports:
        for q in r.misses:
            print(f"  {r.name}: {q}")

    q = QUESTIONS[0][0]
    print(f"\nTop chunk for {q!r}:")
    for name in ("fixed-size (40 words, 10 overlap)", "by headings"):
        score, chunk = search(STRATEGIES[name](HANDBOOK), q)[0]
        print(f"  {name} (score {score:.2f}): {chunk.context[:110]}...")


if __name__ == "__main__":
    main()
