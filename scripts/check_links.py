"""Check every internal link and anchor in the repository's Markdown files.

Usage:
    python scripts/check_links.py

It verifies that:
  * every relative link points to a file or folder that exists;
  * every `#anchor` matches a heading in the target file (GitHub slug rules);
  * no heading contains U+FE0F (the invisible emoji variation selector), because
    GitHub keeps it in anchors and MkDocs drops it, which breaks links on one of them.

External links (http/https) are checked in CI by lychee, not here.
Exit code is 1 if any problem is found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "site", "node_modules", "__pycache__", ".pytest_cache", "templates"}

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# [text](target "title")  and  ![alt](target)
MD_LINK = re.compile(r"!?\[(?:[^\]\[]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_LINK = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""")
HTML_ANCHOR = re.compile(r"""<a\s+[^>]*(?:id|name)\s*=\s*["']([^"']+)["']""")
INLINE_CODE = re.compile(r"`[^`]*`")


def github_slug(text: str) -> str:
    """Approximate GitHub's heading-anchor algorithm."""
    text = re.sub(r"<[^>]+>", "", text)  # HTML tags
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> their text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)  # drop punctuation and emoji, keep letters/digits/_/-/space
    return text.replace(" ", "-")


def markdown_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md") if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    )


def scan(path: Path) -> tuple[set[str], list[tuple[int, str]], list[str]]:
    """Return (anchors, [(line_no, link)], problems) for one file."""
    anchors: set[str] = set()
    links: list[tuple[int, str]] = []
    problems: list[str] = []
    counts: dict[str, int] = {}
    in_fence = False
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            if "️" in m.group(2):
                problems.append(f"{no}: heading contains U+FE0F (use an emoji without a variation selector)")
            slug = github_slug(m.group(2))
            n = counts.get(slug, 0)
            anchors.add(slug if n == 0 else f"{slug}-{n}")
            counts[slug] = n + 1
        anchors.update(HTML_ANCHOR.findall(line))
        stripped = INLINE_CODE.sub("", line)
        for target in MD_LINK.findall(stripped) + HTML_LINK.findall(stripped):
            links.append((no, target))
    return anchors, links, problems


def main() -> int:
    files = markdown_files()
    cache: dict[Path, tuple[set[str], list[tuple[int, str]], list[str]]] = {f: scan(f) for f in files}
    errors: list[str] = []
    checked = 0

    for f in files:
        anchors, links, problems = cache[f]
        rel_f = f.relative_to(ROOT).as_posix()
        errors += [f"{rel_f}:{p}" for p in problems]
        for no, target in links:
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):  # http:, https:, mailto:, ...
                continue
            checked += 1
            path_part, _, anchor = target.partition("#")
            path_part = unquote(path_part)
            dest = f if not path_part else (f.parent / path_part).resolve()
            if not dest.exists():
                errors.append(f"{rel_f}:{no}: broken link -> {target}")
                continue
            if anchor:
                if dest.is_dir() or dest.suffix != ".md":
                    continue
                if dest not in cache:
                    cache[dest] = scan(dest)
                if unquote(anchor) not in cache[dest][0]:
                    errors.append(f"{rel_f}:{no}: missing anchor -> {target}")

    if errors:
        print("\n".join(errors))
        print(f"\n✗ {len(errors)} problem(s) in {len(files)} files ({checked} internal links checked).")
        return 1
    print(f"✓ All {checked} internal links in {len(files)} Markdown files resolve.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # emoji output on Windows consoles
    sys.exit(main())
