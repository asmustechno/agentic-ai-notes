"""Keep every navigation surface in sync with curriculum.yml.

Usage:
    python scripts/build_nav.py          # write changes
    python scripts/build_nav.py --check  # exit 1 if anything is out of date (used in CI)

What it maintains:
    README.md            table of contents between <!-- TOC:START --> and <!-- TOC:END -->
    SUMMARY.md           the whole file
    mkdocs.yml           the nav between "# NAV:START" and "# NAV:END"
    docs/NN-*/README.md  page list between <!-- PAGES:START --> and <!-- PAGES:END -->
    every page           the breadcrumb (first line, starts with 🏠) and the footer
                         (everything after the <!-- FOOTER --> marker)

Missing chapter READMEs and pages are created as stubs. Existing text outside
the markers is never touched, so you can write pages freely.
"""

from __future__ import annotations

import argparse
import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BADGES = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
LEVEL_NAMES = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
FOOTER_MARKER = "<!-- FOOTER -->"


@dataclass
class Page:
    chapter: "Chapter"
    index: int  # 1-based position inside the chapter
    slug: str
    title: str
    level: str
    minutes: int
    desc: str

    @property
    def number(self) -> str:
        """Human number, e.g. '2.3'."""
        return f"{int(self.chapter.id)}.{self.index}"

    @property
    def path(self) -> str:
        """Repo-relative POSIX path, e.g. 'docs/02-the-agent-loop/02.3-x.md'."""
        return f"{self.chapter.dir}/{self.chapter.id}.{self.index}-{self.slug}.md"

    @property
    def label(self) -> str:
        return f"{self.number} {self.title}"


@dataclass
class Chapter:
    id: str
    slug: str
    title: str
    desc: str
    pages: list[Page]

    @property
    def dir(self) -> str:
        return f"docs/{self.id}-{self.slug}"

    @property
    def readme(self) -> str:
        return f"{self.dir}/README.md"

    @property
    def label(self) -> str:
        return f"{self.id} · {self.title}"

    @property
    def minutes(self) -> int:
        return sum(p.minutes for p in self.pages)


def load_curriculum() -> list[Chapter]:
    data = yaml.safe_load((ROOT / "curriculum.yml").read_text(encoding="utf-8"))
    chapters: list[Chapter] = []
    for ch in data["chapters"]:
        chapter = Chapter(id=str(ch["id"]), slug=ch["slug"], title=ch["title"], desc=ch["desc"], pages=[])
        for i, p in enumerate(ch["pages"], start=1):
            if p["level"] not in BADGES:
                raise ValueError(f"Unknown level {p['level']!r} for page {p['slug']}")
            chapter.pages.append(
                Page(chapter, i, p["slug"], str(p["title"]), p["level"], int(p["min"]), p["desc"])
            )
        chapters.append(chapter)
    return chapters


def rel(from_file: str, to_file: str) -> str:
    """Relative link from one repo file to another, './'-prefixed when in the same folder."""
    link = posixpath.relpath(to_file, posixpath.dirname(from_file) or ".")
    return link if link.startswith("../") else f"./{link}"


# ---------------------------------------------------------------- generators


def readme_toc(chapters: list[Chapter]) -> str:
    lines: list[str] = []
    for ch in chapters:
        lines += [
            f"### [{ch.label}]({ch.readme})",
            "",
            f"{ch.desc} *(~{ch.minutes} min)*",
            "",
            "| Page | What you'll learn | Level |",
            "| --- | --- | --- |",
        ]
        for p in ch.pages:
            lines.append(f"| [{p.label}]({p.path}) | {p.desc} | {BADGES[p.level]} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summary_md(chapters: list[Chapter]) -> str:
    lines = [
        "# Summary",
        "",
        "Every page in reading order. Generated from `curriculum.yml` by `scripts/build_nav.py`; do not edit by hand.",
        "",
        "- [Home](README.md)",
        "- [Roadmap](ROADMAP.md)",
    ]
    for ch in chapters:
        lines.append(f"- [{ch.label}]({ch.readme})")
        for p in ch.pages:
            lines.append(f"  - [{p.label}]({p.path})")
    lines += ["- [Glossary](GLOSSARY.md)", "- [Cheatsheet](CHEATSHEET.md)", "- [Contributing](CONTRIBUTING.md)", ""]
    return "\n".join(lines)


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def mkdocs_nav(chapters: list[Chapter]) -> str:
    lines = [
        "nav:",
        "  - Home: README.md",
        "  - Roadmap: ROADMAP.md",
    ]
    for ch in chapters:
        lines.append(f"  - {yaml_str(ch.label)}:")
        lines.append(f"      - Overview: {ch.readme}")
        for p in ch.pages:
            lines.append(f"      - {yaml_str(p.label)}: {p.path}")
    lines += [
        "  - Glossary: GLOSSARY.md",
        "  - Cheatsheet: CHEATSHEET.md",
        "  - Contributing: CONTRIBUTING.md",
    ]
    return "\n".join(lines) + "\n"


def chapter_pages_list(ch: Chapter) -> str:
    lines = ["| # | Page | Level | Time |", "| --- | --- | --- | --- |"]
    for p in ch.pages:
        lines.append(
            f"| {p.number} | [{p.title}]({rel(ch.readme, p.path)}) — {p.desc} "
            f"| {BADGES[p.level]} {LEVEL_NAMES[p.level]} | ~{p.minutes} min |"
        )
    return "\n".join(lines) + "\n"


def breadcrumb(p: Page) -> str:
    return f"🏠 [Home]({rel(p.path, 'README.md')}) › [{p.chapter.label}](./README.md) › {p.label}"


def chapter_breadcrumb(ch: Chapter) -> str:
    return f"🏠 [Home]({rel(ch.readme, 'README.md')}) › {ch.label}"


def page_footer(p: Page, prev: Page | None, nxt: Page | None) -> str:
    if prev is None:
        prev_link = f"[Home]({rel(p.path, 'README.md')})"
    else:
        prev_link = f"[{prev.label}]({rel(p.path, prev.path)})"
    if nxt is None:
        next_link = f"[Cheatsheet: every pattern on one page]({rel(p.path, 'CHEATSHEET.md')})"
    elif nxt.chapter is not p.chapter:
        next_link = f"[{nxt.chapter.label} → {nxt.label}]({rel(p.path, nxt.path)})"
    else:
        next_link = f"[{nxt.label}]({rel(p.path, nxt.path)})"
    return (
        "---\n\n"
        f"⬅️ **Previous:** {prev_link} ·\n"
        f"🏠 [Chapter home](./README.md) ·\n"
        f"➡️ **Next:** {next_link}\n"
    )


def chapter_footer(ch: Chapter, prev: Chapter | None, nxt: Chapter | None) -> str:
    prev_link = f"[{prev.label}]({rel(ch.readme, prev.readme)})" if prev else f"[Home]({rel(ch.readme, 'README.md')})"
    next_link = f"[{nxt.label}]({rel(ch.readme, nxt.readme)})" if nxt else f"[Cheatsheet]({rel(ch.readme, 'CHEATSHEET.md')})"
    first = f"[{ch.pages[0].label}]({rel(ch.readme, ch.pages[0].path)})"
    return (
        "---\n\n"
        f"⬅️ **Previous chapter:** {prev_link} ·\n"
        f"▶️ **Start reading:** {first} ·\n"
        f"➡️ **Next chapter:** {next_link}\n"
    )


# ---------------------------------------------------------------- stubs


def page_stub(p: Page) -> str:
    return (
        f"{breadcrumb(p)}\n\n"
        f"# {p.label}\n\n"
        f"> **Difficulty:** {BADGES[p.level]} {LEVEL_NAMES[p.level]} · **Reading time:** ~{p.minutes} min\n\n"
        f"**In one sentence:** {p.desc}\n\n"
        "> 🚧 **This page is planned but not written yet.** "
        "See the [chapter overview](./README.md) for what is available now.\n\n"
        f"{FOOTER_MARKER}\n\n"
    )


def chapter_stub(ch: Chapter) -> str:
    return (
        f"{chapter_breadcrumb(ch)}\n\n"
        f"# {ch.label}\n\n"
        f"> **Estimated reading time:** ~{ch.minutes} min\n\n"
        f"{ch.desc}\n\n"
        "> 🚧 **This chapter is planned but not written yet.**\n\n"
        "## 📄 Pages in this chapter\n\n"
        "<!-- PAGES:START -->\n<!-- PAGES:END -->\n\n"
        f"{FOOTER_MARKER}\n\n"
    )


# ---------------------------------------------------------------- splicing


def replace_between(text: str, start: str, end: str, body: str, file: str) -> str:
    try:
        head, rest = text.split(start, 1)
        _, tail = rest.split(end, 1)
    except ValueError:
        raise SystemExit(f"{file}: missing markers {start!r} / {end!r}") from None
    return f"{head}{start}\n{body}{end}{tail}"


def set_breadcrumb(text: str, crumb: str) -> str:
    first, sep, rest = text.partition("\n")
    if first.startswith("🏠"):
        return crumb + sep + rest
    return f"{crumb}\n\n{text}"


def set_footer(text: str, footer: str, file: str) -> str:
    if FOOTER_MARKER not in text:
        raise SystemExit(f"{file}: missing {FOOTER_MARKER} marker")
    head = text.rsplit(FOOTER_MARKER, 1)[0]
    return f"{head}{FOOTER_MARKER}\n\n{footer}"


def build(chapters: list[Chapter]) -> dict[str, str]:
    """Return {repo-relative path: desired content} for every managed file."""
    out: dict[str, str] = {}

    def current(path: str, default: str) -> str:
        f = ROOT / path
        return f.read_text(encoding="utf-8") if f.exists() else default

    out["README.md"] = replace_between(
        current("README.md", ""), "<!-- TOC:START -->", "<!-- TOC:END -->", readme_toc(chapters), "README.md"
    )
    out["SUMMARY.md"] = summary_md(chapters)
    out["mkdocs.yml"] = replace_between(
        current("mkdocs.yml", ""), "# NAV:START", "# NAV:END", mkdocs_nav(chapters), "mkdocs.yml"
    )

    all_pages = [p for ch in chapters for p in ch.pages]
    for ci, ch in enumerate(chapters):
        text = current(ch.readme, chapter_stub(ch))
        text = set_breadcrumb(text, chapter_breadcrumb(ch))
        text = replace_between(text, "<!-- PAGES:START -->", "<!-- PAGES:END -->", chapter_pages_list(ch), ch.readme)
        prev_ch = chapters[ci - 1] if ci > 0 else None
        next_ch = chapters[ci + 1] if ci + 1 < len(chapters) else None
        out[ch.readme] = set_footer(text, chapter_footer(ch, prev_ch, next_ch), ch.readme)

    for pi, p in enumerate(all_pages):
        text = current(p.path, page_stub(p))
        text = set_breadcrumb(text, breadcrumb(p))
        prev = all_pages[pi - 1] if pi > 0 else None
        nxt = all_pages[pi + 1] if pi + 1 < len(all_pages) else None
        out[p.path] = set_footer(text, page_footer(p, prev, nxt), p.path)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if any managed file is out of date")
    args = parser.parse_args()

    chapters = load_curriculum()
    stale: list[str] = []
    for path, content in build(chapters).items():
        f = ROOT / path
        old = f.read_text(encoding="utf-8") if f.exists() else None
        if old == content:
            continue
        stale.append(path)
        if not args.check:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8", newline="\n")

    pages = sum(len(c.pages) for c in chapters)
    if args.check:
        if stale:
            print("Out of date (run `python scripts/build_nav.py`):")
            print("\n".join(f"  - {s}" for s in stale))
            return 1
        print(f"Navigation is in sync: {len(chapters)} chapters, {pages} pages.")
        return 0
    print(f"Updated {len(stale)} file(s). {len(chapters)} chapters, {pages} pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
