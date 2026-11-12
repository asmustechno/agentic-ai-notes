"""The reflection pattern: draft -> critique -> revise, until the critic is happy.

One model plays two roles with two different system prompts:

    writer  : produces a draft, then revises it using the critique
    critic  : lists concrete problems, or replies exactly "NO ISSUES"

The loop stops when the critic says "NO ISSUES" or after `max_rounds` critiques.

    python main.py                  # from this folder
    python 08-reflection/main.py    # from examples/

Read alongside docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

WRITER_SYSTEM = (
    "You write short release notes for non-technical users of a budgeting app. "
    "Reply with the release note only, no preamble."
)
CRITIC_SYSTEM = (
    "You review release notes written for NON-TECHNICAL users. Check: (1) no jargon, "
    "(2) says what changed for the user, (3) says what, if anything, the user should do, "
    "(4) at most two sentences. List each problem on its own line starting with '- '. "
    "If there are no problems, reply exactly: NO ISSUES"
)
NO_ISSUES = "NO ISSUES"

TASK = "Write a release note for version 2.3. It fixes the bug where CSV exports were sometimes empty."

SCRIPT = [
    # 1. draft
    "v2.3: Fixed a race condition in the CSV serializer that caused zero-byte exports.",
    # 2. critique of the draft
    "- Jargon: 'race condition', 'serializer' and 'zero-byte' mean nothing to most users.\n"
    "- Does not say what the user should do if an earlier export was empty.",
    # 3. revision
    "Version 2.3 fixes a problem that sometimes made exported spreadsheets (CSV files) empty. "
    "If an export you made recently was blank, please export it again.",
    # 4. critique of the revision
    "NO ISSUES",
]


@dataclass
class ReflectionResult:
    """The final text plus every draft and critique, so you can see how it improved."""

    final: str
    drafts: list[str] = field(default_factory=list)
    critiques: list[str] = field(default_factory=list)
    stopped_because: str = ""


def is_clean(critique: str) -> bool:
    """True if the critic found nothing to fix. Strict on purpose: 'No issues, but...' is not clean."""
    return critique.strip().rstrip(".").upper() == NO_ISSUES


def reflect(llm: LLM, task: str, *, max_rounds: int = 3) -> ReflectionResult:
    """Draft, then alternate critique and revision until the critic is satisfied or rounds run out."""
    draft = llm.chat([user(task)], system=WRITER_SYSTEM).text.strip()  # 1. draft
    result = ReflectionResult(final=draft, drafts=[draft])

    for _ in range(max_rounds):
        critique = llm.chat(  # 2. critique: a fresh conversation, so the critic sees only the task and draft
            [user(f"Task:\n{task}\n\nRelease note to review:\n{draft}")],
            system=CRITIC_SYSTEM,
        ).text.strip()
        result.critiques.append(critique)
        if is_clean(critique):
            result.stopped_because = "critic found no issues"
            return result

        draft = llm.chat(  # 3. revise, using the critique as feedback
            [
                user(
                    f"Task:\n{task}\n\nYour previous draft:\n{draft}\n\n"
                    f"A reviewer found these problems:\n{critique}\n\n"
                    "Rewrite the release note to fix every problem. Reply with the new note only."
                )
            ],
            system=WRITER_SYSTEM,
        ).text.strip()
        result.drafts.append(draft)
        result.final = draft

    result.stopped_because = f"hit max_rounds={max_rounds}"
    return result


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    print(f"Task: {TASK}\n")
    result = reflect(llm, TASK)
    for i, draft in enumerate(result.drafts):
        print(f"--- draft {i + 1}\n{draft}\n")
        if i < len(result.critiques):
            print(f"--- critique {i + 1}\n{result.critiques[i]}\n")
    print(f"Stopped: {result.stopped_because}. Model calls: {len(result.drafts) + len(result.critiques)}")


if __name__ == "__main__":
    main()
