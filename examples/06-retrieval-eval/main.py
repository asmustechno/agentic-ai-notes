"""Measure retrieval quality, then improve it with hybrid search and re-ranking.

    python main.py                       # from this folder
    python 06-retrieval-eval/main.py     # from examples/

Four retrievers over the same small help-centre corpus:

  * BM25 (keyword search);
  * "vector" search with a toy character-trigram embedding;
  * hybrid: both lists merged with reciprocal rank fusion (RRF);
  * hybrid + re-rank: a second pass that scores (query, document) pairs together.

Each is scored on a tiny labelled eval set with recall@k, precision@k, MRR and nDCG@k.

Everything is pure Python and offline. Real systems use an embedding model for
the vector side and a trained cross-encoder model as the re-ranker; the toy
versions here only show the plumbing and the metrics.

Read alongside docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md.
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable (kept for consistency)

# --------------------------------------------------------------------------- corpus and labelled eval set

DOCS: dict[str, str] = {
    "refunds": "Refund policy. Annual plans can be refunded within 30 days of purchase. Monthly plans are not refundable.",
    "cancel": "Ending your plan. Open Billing, choose Cancel plan and confirm. "
    "Cancellation takes effect at the end of the billing period.",
    "invoices": "Invoices. Download invoices as PDF files from the Billing page. Invoices show VAT where it applies.",
    "errors": "Error codes. Every error code is E- followed by four digits. "
    "Codes starting E-4 are billing errors and codes starting E-5 are database errors.",
    "err-e4021": "E-4021: payment method declined. Update your card under Billing and retry the payment.",
    "err-e5003": "E-5003: restore timed out. Restores of very large databases can take longer, so contact support.",
    "restore": "Restoring a backup. Open the database, choose Backups, pick a date and click Restore. "
    "Restoring replaces the current data.",
    "backups": "Backup schedule. Databases are backed up daily at 02:00 UTC and kept for 7 to 90 days depending on plan.",
    "sso": "Single sign-on. Connect Okta or Azure AD under Settings, Security. Available on the Business plan.",
    "2fa": "Two-factor authentication. Turn on 2FA under Settings, Security, using an authenticator app.",
    "password": "Resetting your password. Click Forgot password on the login page and follow the link we email you.",
    "regions": "Data regions. Projects are hosted in Frankfurt or Virginia. You choose the region when you create a project.",
    "limits": "API rate limits. Requests over your monthly limit return HTTP 429 Too Many Requests.",
}

# query -> {doc id: graded relevance}. 2 = answers it, 1 = useful background. Unlisted docs count as 0.
EVAL_SET: dict[str, dict[str, int]] = {
    "cancelling my subscription": {"cancel": 2, "refunds": 1},
    "error E-4021": {"err-e4021": 2, "errors": 1},
    "refund for a yearly plan": {"refunds": 2},
    "restore timed out": {"err-e5003": 2, "restore": 1},
    "how long are backups kept": {"backups": 2},
    "two factor login": {"2fa": 2},
    "log in with Okta": {"sso": 2},
    "forgot my password": {"password": 2},
    "HTTP 429": {"limits": 2},
    "where is my data hosted": {"regions": 2},
    "E-5003": {"err-e5003": 2, "errors": 1},
    "download a PDF invoice": {"invoices": 2},
}

Ranking = list[str]  # doc ids, best first

# --------------------------------------------------------------------------- retriever 1: BM25

STOPWORDS = set("a an and are as at by can do for from how i in is it my of on or the to we what where with you your".split())


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()) if w not in STOPWORDS]


class BM25:
    """Okapi BM25: rewards documents that contain rare query words, with diminishing returns for repeats."""

    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75) -> None:
        self.ids = list(docs)
        self.tfs = [Counter(words(docs[d])) for d in self.ids]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = sum(self.lens) / len(self.lens)
        self.k1, self.b = k1, b
        n_docs = len(self.ids)
        df = Counter(w for tf in self.tfs for w in tf)  # how many documents contain each word
        self.idf = {w: math.log((n_docs - n + 0.5) / (n + 0.5) + 1) for w, n in df.items()}

    def score(self, query: str, i: int) -> float:
        tf, length, s = self.tfs[i], self.lens[i], 0.0
        for w in words(query):
            if w in tf:
                f = tf[w]
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg_len))
        return s

    def search(self, query: str, k: int = 10) -> Ranking:
        scored = [(self.score(query, i), d) for i, d in enumerate(self.ids)]
        return [d for s, d in sorted(scored, key=lambda p: -p[0]) if s > 0][:k]


# --------------------------------------------------------------------------- retriever 2: toy "vector" search

DIM = 1024


def embed(text: str) -> list[float]:
    """Hashed character trigrams, normalised. "cancel" and "cancellation" share trigrams, so they land close.

    A real embedding model captures meaning ("money back" ~ "refund"); this toy only captures spelling.
    """
    vec = [0.0] * DIM
    for w in words(text):
        padded = f" {w} "
        for i in range(len(padded) - 2):
            vec[int(hashlib.md5(padded[i : i + 3].encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class VectorIndex:
    def __init__(self, docs: dict[str, str]) -> None:
        self.vectors = {d: embed(t) for d, t in docs.items()}

    def search(self, query: str, k: int = 10) -> Ranking:
        q = embed(query)
        scored = [(sum(a * b for a, b in zip(q, v)), d) for d, v in self.vectors.items()]
        return [d for _, d in sorted(scored, key=lambda p: -p[0])][:k]


# --------------------------------------------------------------------------- hybrid: reciprocal rank fusion


def rrf(rankings: list[Ranking], k: int = 60) -> Ranking:
    """Reciprocal rank fusion: score(d) = sum over lists of 1 / (k + rank of d). Uses ranks only, not raw scores."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, d in enumerate(ranking, start=1):
            scores[d] = scores.get(d, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda d: -scores[d])


# --------------------------------------------------------------------------- re-ranker (a stand-in for a cross-encoder)


def stems(text: str) -> list[str]:
    """Words split on hyphens too, cut to five letters: a crude stemmer ("cancelling", "cancellation" -> "cance")."""
    return [w[:5] for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


_STEM_DF = Counter(st for text in DOCS.values() for st in set(stems(text)))


def _weight(st: str) -> float:
    """Rare stems matter more (an IDF weight), like in BM25."""
    return math.log((len(DOCS) + 1) / (_STEM_DF.get(st, 0) + 0.5))


def rerank_score(query: str, doc: str) -> float:
    """Look at the query and the document *together*, as a cross-encoder does.

    Score = the weighted share of query words the document covers, plus a bonus for
    query word pairs that appear side by side in the document. A real re-ranker is a
    trained model that reads both texts at once; this toy only imitates the interface.
    """
    q, d = stems(query), stems(doc)
    if not q:
        return 0.0
    coverage = sum(_weight(w) for w in q if w in d) / sum(_weight(w) for w in q)
    pairs, doc_pairs = list(zip(q, q[1:])), set(zip(d, d[1:]))
    adjacency = sum(p in doc_pairs for p in pairs) / len(pairs) if pairs else 0.0
    return coverage + 0.5 * adjacency


def rerank(query: str, candidates: Ranking, docs: dict[str, str] = DOCS) -> Ranking:
    """Re-order a short candidate list. Stable: ties keep their first-stage order."""
    return sorted(candidates, key=lambda d: -rerank_score(query, docs[d]))


# --------------------------------------------------------------------------- metrics


def precision_at_k(ranking: Ranking, relevant: dict[str, int], k: int) -> float:
    """Of the top k results, what fraction are relevant?"""
    return sum(1 for d in ranking[:k] if relevant.get(d, 0) > 0) / k


def recall_at_k(ranking: Ranking, relevant: dict[str, int], k: int) -> float:
    """Of all the relevant documents, what fraction made it into the top k?"""
    total = sum(1 for g in relevant.values() if g > 0)
    return sum(1 for d in ranking[:k] if relevant.get(d, 0) > 0) / total if total else 0.0


def reciprocal_rank(ranking: Ranking, relevant: dict[str, int]) -> float:
    """1 / position of the first relevant result (0 if there is none). Averaged over queries, this is MRR."""
    for rank, d in enumerate(ranking, start=1):
        if relevant.get(d, 0) > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranking: Ranking, relevant: dict[str, int], k: int) -> float:
    """Normalised discounted cumulative gain: graded relevance, discounted by log2(position + 1),
    divided by the score of the perfect ordering, so 1.0 means "ideal"."""

    def dcg(grades: list[int]) -> float:
        return sum(g / math.log2(i + 2) for i, g in enumerate(grades))

    ideal = dcg(sorted(relevant.values(), reverse=True)[:k])
    return dcg([relevant.get(d, 0) for d in ranking[:k]]) / ideal if ideal else 0.0


def evaluate(search: Callable[[str], Ranking], k: int = 3) -> dict[str, float]:
    """Average each metric over the eval set."""
    totals = {f"recall@{k}": 0.0, f"precision@{k}": 0.0, "MRR": 0.0, f"nDCG@{k}": 0.0}
    for query, relevant in EVAL_SET.items():
        ranking = search(query)
        totals[f"recall@{k}"] += recall_at_k(ranking, relevant, k)
        totals[f"precision@{k}"] += precision_at_k(ranking, relevant, k)
        totals["MRR"] += reciprocal_rank(ranking, relevant)
        totals[f"nDCG@{k}"] += ndcg_at_k(ranking, relevant, k)
    return {name: value / len(EVAL_SET) for name, value in totals.items()}


# --------------------------------------------------------------------------- run it

bm25 = BM25(DOCS)
vectors = VectorIndex(DOCS)


def hybrid(query: str) -> Ranking:
    return rrf([bm25.search(query), vectors.search(query)])


def hybrid_rerank(query: str, n_candidates: int = 10) -> Ranking:
    return rerank(query, hybrid(query)[:n_candidates])


RETRIEVERS: dict[str, Callable[[str], Ranking]] = {
    "BM25": bm25.search,
    "vector (trigram toy)": vectors.search,
    "hybrid (RRF)": hybrid,
    "hybrid + re-rank": hybrid_rerank,
}


def main() -> None:
    k = 3
    results = {name: evaluate(fn, k) for name, fn in RETRIEVERS.items()}
    metrics = list(next(iter(results.values())))
    print(f"{'Retriever':22}" + "".join(f"{m:>14}" for m in metrics))
    for name, scores in results.items():
        print(f"{name:22}" + "".join(f"{scores[m]:>14.2f}" for m in metrics))

    print("\nTop 3 per retriever:")
    for query in ("cancelling my subscription", "how long are backups kept"):
        print(f"  {query!r}  (relevant: {EVAL_SET[query]})")
        for name, fn in RETRIEVERS.items():
            print(f"    {name:22} {fn(query)[:k]}")


if __name__ == "__main__":
    main()
