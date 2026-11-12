"""Chunking strategies split the document as intended, and structure-aware ones retrieve better."""

from common.testing import load_example

main = load_example(__file__)


def test_embedding_is_stable_and_normalised() -> None:
    a, b = main.embed("Backups are kept for 30 days"), main.embed("Backups are kept for 30 days")
    assert a == b  # hashlib, not hash(): identical across runs
    assert abs(sum(v * v for v in a) - 1.0) < 1e-9
    assert main.cosine(a, main.embed("backups kept 30 days")) > 0.99  # stop words and case are ignored


def test_fixed_size_windows_overlap() -> None:
    doc = " ".join(f"w{i}" for i in range(100))
    chunks = main.fixed_size(doc, size=40, overlap=10)
    assert all(len(c.text.split()) <= 40 for c in chunks)
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert first[-10:] == second[:10]  # the last 10 words repeat at the start of the next chunk
    assert chunks[-1].text.split()[-1] == "w99"  # nothing is lost at the end


def test_sentence_packing_never_cuts_a_sentence() -> None:
    sentences = set(main._body_sentences(main.HANDBOOK))
    for chunk in main.sentence_packed(main.HANDBOOK):
        for s in main.split_sentences(chunk.text):
            assert s in sentences


def test_headings_keep_their_path() -> None:
    texts = [c.text for c in main.by_headings(main.HANDBOOK)]
    assert any(t.startswith("Plans > Pro plan: The Pro plan costs $49") for t in texts)
    assert any(t.startswith("Security: ") for t in texts)


def test_parent_child_searches_children_but_returns_parent() -> None:
    chunks = main.parent_child(main.HANDBOOK)
    _, best = main.search(chunks, "How long are backups kept on the Pro plan?")[0]
    assert best.text == "Plans > Pro plan: Backups are kept for 30 days."  # the small child matched
    assert best.context.startswith("Plans > Pro plan: The Pro plan costs $49")  # the parent is returned


def test_fixed_size_returns_the_wrong_plan() -> None:
    """The motivating failure: without heading context, the Starter plan's backup rule wins."""
    _, best = main.search(main.fixed_size(main.HANDBOOK), "How long are backups kept on the Pro plan?")[0]
    assert "Backups are kept for 7 days" in best.context
    assert "30 days" not in best.context


def test_structure_aware_strategies_score_best() -> None:
    reports = {name: main.evaluate(name, fn) for name, fn in main.STRATEGIES.items()}
    assert reports["by headings"].hits == len(main.QUESTIONS)
    assert reports["parent-child"].hits == len(main.QUESTIONS)
    assert reports["fixed-size (40 words, 10 overlap)"].hits < len(main.QUESTIONS)
