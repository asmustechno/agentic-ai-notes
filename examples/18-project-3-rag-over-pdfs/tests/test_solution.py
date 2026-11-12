"""Acceptance tests for Project 3. Offline, with MockLLM and the sample documents.

By default they test solution/main.py. Set PROJECT_TARGET=starter to test your own work.
The PDF tests run only when pypdf is installed (pip install -r requirements.txt).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from common import MockLLM


def load(target: str | None = None) -> ModuleType:
    """Import <project>/<target>/main.py under a unique module name."""
    target = target or os.getenv("PROJECT_TARGET", "solution")
    path = Path(__file__).resolve().parent.parent / target / "main.py"
    name = f"p18_3_rag_{target}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader, f"cannot load {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


app = load()
SAMPLES = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture(scope="module")
def index():  # noqa: ANN201
    return app.build_index(SAMPLES)


# --------------------------------------------------------------------------- ingest and chunk


def test_loads_text_and_markdown_without_pypdf(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("# Title\n\nHello.", encoding="utf-8")
    (tmp_path / "a.txt").write_text("Plain text.", encoding="utf-8")
    (tmp_path / "ignore.png").write_bytes(b"\x89PNG")
    pages = app.load_documents(tmp_path)
    assert [(p.source, p.page) for p in pages] == [("a.txt", None), ("b.md", None)]


def test_chunks_keep_their_section_and_respect_the_size_limit() -> None:
    long_para = " ".join(f"w{i}" for i in range(200))
    page = app.Page("doc.md", f"# Intro\n\nShort first paragraph.\n\n## Big\n\n{long_para}")
    chunks = app.chunk_pages([page], max_words=80, overlap=15)
    assert [c.id for c in chunks] == [f"doc.md#{i}" for i in range(1, len(chunks) + 1)]
    assert chunks[0].section == "Intro" and chunks[0].text == "Short first paragraph."
    big = [c for c in chunks if c.section == "Big"]
    assert all(len(c.text.split()) <= 80 for c in big)
    assert big[0].text.split()[-15:] == big[1].text.split()[:15]  # windows overlap
    assert "w199" in big[-1].text  # nothing lost at the end


# --------------------------------------------------------------------------- embed and search


def test_embedder_is_deterministic_normalised_and_similarity_tracks_shared_words() -> None:
    emb = app.HashedEmbedder(dim=256)
    a, b, c = emb.embed("hotel limit London"), emb.embed("London hotel nightly limit"), emb.embed("VPN on public Wi-Fi")
    assert a == emb.embed("hotel limit London")
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9
    assert app.cosine(a, b) > 0.5 > app.cosine(a, c)
    assert emb.embed("") == [0.0] * 256


def test_search_finds_the_right_passages(index) -> None:  # noqa: ANN001
    assert index.search("hotel limit per night London")[0].chunk.id == "acme-expenses-policy.md#4"
    assert index.search("work from another country")[0].chunk.id == "acme-remote-work-guide.md#5"
    assert index.search("receipt taxi")[0].chunk.section == "Receipts and deadlines"
    assert index.search("xylophone quantum") == []


def test_index_round_trips_and_refuses_a_different_embedder(index, tmp_path: Path) -> None:  # noqa: ANN001
    path = tmp_path / "index.json"
    index.save(path)
    again = app.VectorIndex.load(path)
    assert [c.id for c in again.chunks] == [c.id for c in index.chunks]
    assert again.search("VPN")[0].chunk.id == index.search("VPN")[0].chunk.id
    with pytest.raises(ValueError, match="rebuild"):
        app.VectorIndex.load(path, app.HashedEmbedder(dim=64))


# --------------------------------------------------------------------------- the agent


def test_demo_answers_with_checked_citations(index) -> None:  # noqa: ANN001
    llm = MockLLM(app.DEMO_SCRIPT)
    answer = app.RagAgent(llm, index).ask(app.DEMO_QUESTION)
    assert answer.citations == ["acme-expenses-policy.md#4", "acme-expenses-policy.md#7"]
    assert answer.unsupported == []
    assert llm.calls[0]["tools"][0]["name"] == "search_docs"
    assert "Answer ONLY from the passages" in llm.calls[0]["system"]
    passages = json.loads(llm.calls[1]["messages"][-2]["content"])  # first of the two tool results
    assert passages[0]["id"] == "acme-expenses-policy.md#4" and "€250" in passages[0]["text"]


def test_citations_to_passages_never_retrieved_are_flagged(index) -> None:  # noqa: ANN001
    llm = MockLLM([MockLLM.tool_call("search_docs", {"query": "VPN"}), "Use the VPN [acme-remote-work-guide.md#6] [made-up.md#1]."])
    answer = app.RagAgent(llm, index).ask("VPN rules?")
    assert answer.citations == ["acme-remote-work-guide.md#6"]
    assert answer.unsupported == ["made-up.md#1"]


def test_not_found_answer_and_bad_tool_calls(index) -> None:  # noqa: ANN001
    llm = MockLLM([MockLLM.tool_call("search_docs", {}), MockLLM.tool_call("search_docs", {"query": "xylophone"}), app.NOT_FOUND])
    answer = app.RagAgent(llm, index).ask("xylophone?")
    assert llm.calls[1]["messages"][-1]["is_error"] is True
    assert json.loads(llm.calls[2]["messages"][-1]["content"]) == []
    assert answer.text == app.NOT_FOUND and answer.citations == []


def test_k_is_clamped(index) -> None:  # noqa: ANN001
    agent = app.RagAgent(MockLLM(), index)
    assert len(agent.search_docs("Acme policy travel remote work", k=50)) <= 5


# --------------------------------------------------------------------------- PDFs (skipped without pypdf)


def make_pdf(pages: list[str]) -> bytes:
    """Build a tiny valid PDF with one line of Helvetica text per page (no PDF library needed)."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", ""]
    kids = []
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {len(objects)} 0 R "
                       "/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def test_pdf_pages_are_extracted_with_page_numbers(tmp_path: Path) -> None:
    pytest.importorskip("pypdf")
    (tmp_path / "report.pdf").write_bytes(make_pdf(["Revenue grew in spring.", "Costs fell in autumn."]))
    pages = app.load_documents(tmp_path)
    assert [(p.source, p.page) for p in pages] == [("report.pdf", 1), ("report.pdf", 2)]
    assert "Costs fell" in pages[1].text
    index = app.VectorIndex()
    index.add(app.chunk_pages(pages))
    hit = index.search("costs autumn")[0].chunk
    assert (hit.source, hit.page) == ("report.pdf", 2)


def test_pdfs_are_skipped_with_a_warning_when_pypdf_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "report.pdf").write_bytes(make_pdf(["Hello."]))
    (tmp_path / "notes.txt").write_text("Notes.", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "pypdf", None)  # makes `import pypdf` raise ImportError
    warnings: list[str] = []
    pages = app.load_documents(tmp_path, warn=warnings.append)
    assert [p.source for p in pages] == ["notes.txt"]
    assert "pypdf" in warnings[0]
