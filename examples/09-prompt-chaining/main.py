"""Prompt chaining: fixed steps, one LLM call each, with code "gates" between them.

    changelog -> [1. extract user-facing changes] -> gate -> [2. write announcement] -> gate
              -> [3. translate to Spanish] -> done

Each gate is plain Python. If a gate fails, the chain stops early with a clear error,
instead of passing bad output to the next step.

    python main.py                       # from this folder
    python 09-prompt-chaining/main.py    # from examples/

Read alongside docs/09-agent-design-patterns/09.1-prompt-chaining.md.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

CHANGELOG = """\
- fix(export): CSV export no longer drops rows with emoji (#812)
- chore(deps): bump httpx 0.27 -> 0.28
- feat(budgets): monthly budgets can now roll over unused money
- refactor(api): split accounts service into two modules
- feat(ui): dark mode for the reports page"""

MAX_WORDS = 80


class GateFailed(Exception):
    """A check between two steps failed, so the chain stopped."""


@dataclass
class ChainResult:
    changes: list[str]
    announcement: str
    translation: str
    log: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- gates: cheap, deterministic checks in code


def gate_changes(text: str) -> list[str]:
    """Step 1 must return a JSON list of 1-10 non-empty strings."""
    try:
        changes = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateFailed(f"step 1 did not return JSON: {exc}") from exc
    if not isinstance(changes, list) or not 1 <= len(changes) <= 10:
        raise GateFailed("step 1 must return a list of 1 to 10 changes")
    if not all(isinstance(c, str) and c.strip() for c in changes):
        raise GateFailed("every change must be a non-empty string")
    return changes


def gate_announcement(text: str) -> str:
    """Step 2 must be short and must not leak internal jargon from the changelog."""
    words = len(text.split())
    if words > MAX_WORDS:
        raise GateFailed(f"announcement is {words} words, limit is {MAX_WORDS}")
    for jargon in ("refactor", "chore", "deps", "#"):
        if jargon in text.lower():
            raise GateFailed(f"announcement contains internal jargon: {jargon!r}")
    return text


# ---------------------------------------------------------------- the chain


def run_chain(llm: LLM, changelog: str) -> ChainResult:
    log: list[str] = []

    # Step 1: extract. One narrow job: pick user-facing changes, as JSON.
    raw = llm.chat(
        [user(f"Changelog:\n{changelog}")],
        system=(
            "From a developer changelog, keep only the changes a USER of the app would notice, "
            "rewritten in plain words. Reply with a JSON list of strings only."
        ),
    ).text
    changes = gate_changes(raw)
    log.append(f"step 1 extract   -> {len(changes)} user-facing changes (gate passed)")

    # Step 2: write. Gets only the clean list, not the noisy changelog.
    bullet_list = "\n".join(f"- {c}" for c in changes)
    announcement = llm.chat(
        [user(f"Changes:\n{bullet_list}")],
        system=f"Write a friendly in-app announcement of these changes in under {MAX_WORDS} words. Text only.",
    ).text.strip()
    gate_announcement(announcement)
    log.append(f"step 2 write     -> {len(announcement.split())} words (gate passed)")

    # Step 3: translate. A separate call does one thing well.
    translation = llm.chat(
        [user(announcement)],
        system="Translate the text into Spanish. Keep the tone. Reply with the translation only.",
    ).text.strip()
    log.append("step 3 translate -> done")

    return ChainResult(changes, announcement, translation, log)


SCRIPT = [
    '["CSV exports now keep rows that contain emoji", '
    '"Unused budget money can roll over to the next month", '
    '"The reports page has a dark mode"]',
    "New this week: unused money in your monthly budgets can now roll over to next month, "
    "the reports page has a dark mode, and CSV exports keep every row, even ones with emoji.",
    "Novedades de esta semana: el dinero que no uses en tus presupuestos mensuales ahora puede pasar "
    "al mes siguiente, la página de informes tiene modo oscuro y las exportaciones CSV conservan "
    "todas las filas, incluso las que tienen emojis.",
]


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    try:
        result = run_chain(llm, CHANGELOG)
    except GateFailed as exc:
        print(f"Chain stopped: {exc}")
        return
    print("\n".join(result.log))
    print(f"\nEnglish:\n{result.announcement}\n\nSpanish:\n{result.translation}")


if __name__ == "__main__":
    main()
