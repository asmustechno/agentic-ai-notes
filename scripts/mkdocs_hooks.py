"""MkDocs hook: point repo-only links at GitHub when building the website.

On GitHub, a link like `[LICENSE](LICENSE)` or `[examples](examples/common/)`
works because GitHub can show any file or folder. The website only contains
Markdown pages and images, so those links would break there.

This hook rewrites, for the website build only, every relative link whose
target is not a published page or image into an absolute GitHub URL:
    folders           -> {repo_url}/tree/main/<path>
    other files       -> {repo_url}/blob/main/<path>
The Markdown files themselves are never changed.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

LINK = re.compile(r"(?<!!)\[(?P<text>(?:[^\]\[]|\[[^\]]*\])*)\]\((?P<target>[^)\s]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
SITE_SUFFIXES = {".md", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
REPO_ONLY_PREFIXES = (".github/", "templates/")


def on_page_markdown(markdown: str, page, config, files) -> str:  # noqa: ANN001 (MkDocs signature)
    repo = (config.get("repo_url") or "").rstrip("/")
    if not repo:
        return markdown
    root = Path(config["config_file_path"]).parent
    page_dir = posixpath.dirname(page.file.src_uri)

    def rewrite(m: re.Match[str]) -> str:
        target = m.group("target")
        if re.match(r"^[a-z][a-z0-9+.-]*:|^#", target, re.I):
            return m.group(0)
        path, _, anchor = target.partition("#")
        repo_path = posixpath.normpath(posixpath.join(page_dir, path))
        if repo_path.startswith(".."):
            return m.group(0)
        is_dir = (root / repo_path).is_dir()
        published = Path(repo_path).suffix.lower() in SITE_SUFFIXES and not repo_path.startswith(REPO_ONLY_PREFIXES)
        if published and not is_dir:
            return m.group(0)
        kind = "tree" if is_dir else "blob"
        url = f"{repo}/{kind}/main/{repo_path}" + (f"#{anchor}" if anchor else "")
        return f"[{m.group('text')}]({url})"

    out: list[str] = []
    in_fence = False
    for line in markdown.splitlines(keepends=True):
        if FENCE.match(line):
            in_fence = not in_fence
        out.append(line if in_fence else LINK.sub(rewrite, line))
    return "".join(out)
