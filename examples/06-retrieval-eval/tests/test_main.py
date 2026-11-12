"""Retrieval metrics, BM25, reciprocal rank fusion and re-ranking behave as defined."""

import math

import pytest

from common.testing import load_example

main = load_example(__file__)

RELEVANT = {"a": 2, "b": 1}  # two relevant docs, "a" more so


def test_precision_and_recall_at_k() -> None:
    ranking = ["x", "a", "y", "b"]
    assert main.precision_at_k(ranking, RELEVANT, 2) == 0.5  # 1 of the top 2 is relevant
    assert main.recall_at_k(ranking, RELEVANT, 2) == 0.5  # found 1 of the 2 relevant docs
    assert main.recall_at_k(ranking, RELEVANT, 4) == 1.0
    assert main.precision_at_k([], RELEVANT, 3) == 0.0


def test_reciprocal_rank() -> None:
    assert main.reciprocal_rank(["a", "x"], RELEVANT) == 1.0
    assert main.reciprocal_rank(["x", "y", "b"], RELEVANT) == pytest.approx(1 / 3)
    assert main.reciprocal_rank(["x", "y"], RELEVANT) == 0.0


def test_ndcg() -> None:
    assert main.ndcg_at_k(["a", "b", "x"], RELEVANT, 3) == pytest.approx(1.0)  # ideal order
    swapped = main.ndcg_at_k(["b", "a", "x"], RELEVANT, 3)
    ideal = 2 / math.log2(2) + 1 / math.log2(3)
    assert swapped == pytest.approx((1 / math.log2(2) + 2 / math.log2(3)) / ideal)
    assert 0 < swapped < 1
    assert main.ndcg_at_k(["x", "y"], RELEVANT, 2) == 0.0


def test_worked_example_numbers() -> None:
    """The 'how long are backups kept' row quoted in the docs."""
    ranking = main.hybrid("how long are backups kept")[:3]
    relevant = main.EVAL_SET["how long are backups kept"]
    assert ranking == ["restore", "backups", "err-e5003"]
    assert main.reciprocal_rank(ranking, relevant) == 0.5
    assert main.ndcg_at_k(ranking, relevant, 3) == pytest.approx(1 / math.log2(3))  # ~0.63


def test_bm25_needs_exact_words() -> None:
    assert main.bm25.search("HTTP 429")[0] == "limits"
    assert main.bm25.search("E-5003")[0] == "err-e5003"
    assert main.bm25.search("cancelling my subscription") == []  # no exact word overlap


def test_trigram_vectors_handle_word_variants() -> None:
    assert main.vectors.search("cancelling my subscription")[0] == "cancel"


def test_rrf_uses_ranks_not_scores() -> None:
    fused = main.rrf([["a", "b", "c"], ["b", "c", "a"]], k=60)
    assert fused[0] == "b"  # ranks 2 and 1 beat ranks 1 and 3
    assert main.rrf([["a"], []]) == ["a"]


def test_reranker_fixes_the_order() -> None:
    assert main.hybrid("how long are backups kept")[0] == "restore"
    assert main.hybrid_rerank("how long are backups kept")[0] == "backups"
    assert main.hybrid_rerank("two factor login")[0] == "2fa"


def test_reranking_improves_every_metric_on_this_set() -> None:
    before, after = main.evaluate(main.hybrid), main.evaluate(main.hybrid_rerank)
    for metric in before:
        assert after[metric] >= before[metric]
    assert after["MRR"] == 1.0
