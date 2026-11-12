"""Episodic, semantic and procedural memory, side by side.

  * semantic   facts about the user and their world ("manager: Priya"), newest value wins
  * episodic   what happened in past runs: the task, what the agent did, how it went
  * procedural how to do the job: rules learned from feedback ("put blockers first")

After each run a "reflection" call asks the model what to keep. Before each run
the agent builds its system prompt from all three stores.

    python main.py                    # from this folder
    python 05-memory-types/main.py    # from examples/

Read alongside docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")


def redact(text: str) -> str:
    """Strip obvious personal data before it is stored. Real systems need more than two regexes."""
    return PHONE.sub("[phone]", EMAIL.sub("[email]", text))


@dataclass
class Episode:
    run: int
    task: str
    summary: str
    outcome: str  # "success" | "needs_revision" | "failure"


@dataclass
class Fact:
    value: str
    updated_run: int
    source: str


@dataclass
class AgentMemory:
    facts: dict[str, Fact] = field(default_factory=dict)  # semantic
    episodes: list[Episode] = field(default_factory=list)  # episodic
    procedures: list[str] = field(default_factory=list)  # procedural

    # ---- writing

    def set_fact(self, key: str, value: str, run: int, source: str) -> None:
        self.facts[key.lower()] = Fact(redact(value), run, source)  # same key: newer value replaces the stale one

    def forget(self, key: str) -> None:
        self.facts.pop(key.lower(), None)

    def add_procedure(self, rule: str) -> None:
        if rule and rule not in self.procedures:
            self.procedures.append(rule)

    # ---- reading

    def relevant_episodes(self, task: str, k: int = 2) -> list[Episode]:
        """Most similar past episodes by shared words (a vector search would go here at scale)."""
        words = set(re.findall(r"[a-z]+", task.lower()))
        scored = [(len(words & set(re.findall(r"[a-z]+", e.task.lower()))), e) for e in self.episodes]
        return [e for score, e in sorted(scored, key=lambda s: (-s[0], -s[1].run)) if score > 0][:k]

    def build_system(self, base: str, task: str) -> str:
        parts = [base]
        if self.procedures:
            parts.append("<procedures>\n" + "\n".join(f"- {p}" for p in self.procedures) + "\n</procedures>")
        if self.facts:
            parts.append("<facts>\n" + "\n".join(f"- {k}: {f.value}" for k, f in self.facts.items()) + "\n</facts>")
        if eps := self.relevant_episodes(task):
            lines = [f"- run {e.run} ({e.outcome}): {e.summary}" for e in eps]
            parts.append("<past_episodes>\n" + "\n".join(lines) + "\n</past_episodes>")
        return "\n\n".join(parts)


BASE = "You draft short internal emails for the user. Follow the procedures. Use the facts. Learn from past episodes."
REFLECT = (
    "Here is a task, your draft and the user's feedback. Reply with JSON only, with keys: "
    '"facts" (object of durable facts about the user or team), "procedure" (one reusable rule, or ""), '
    '"summary" (one sentence about what happened) and "outcome" ("success", "needs_revision" or "failure").\n\n'
)


@dataclass
class EmailAgent:
    llm: LLM
    memory: AgentMemory = field(default_factory=AgentMemory)
    runs: int = 0

    def draft(self, task: str) -> str:
        self.runs += 1
        system = self.memory.build_system(BASE, task)
        return self.llm.chat([user(task)], system=system).text

    def reflect(self, task: str, draft: str, feedback: str) -> dict:
        """Write path: let the model decide what is worth remembering, then store it in the right place."""
        prompt = f"{REFLECT}Task: {task}\n\nDraft:\n{draft}\n\nFeedback: {feedback}"
        raw = self.llm.chat([user(prompt)], system="You extract memories. Output JSON only.").text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}  # never let a bad reflection corrupt memory
        for key, value in (data.get("facts") or {}).items():
            self.memory.set_fact(key, str(value), self.runs, source="reflection")
        self.memory.add_procedure(str(data.get("procedure") or "").strip())
        self.memory.episodes.append(
            Episode(self.runs, task, redact(str(data.get("summary", ""))), str(data.get("outcome", "unknown")))
        )
        return data


TASK = "Draft this week's status email for my manager."
FEEDBACK_1 = ("Too long. Keep it under 30 words and always list blockers first. "
              "FYI my manager is Priya (priya.shah@example.com) and we are the Platform team.")
SCRIPT = [
    # run 1: the draft, then the reflection
    "Hi,\n\nThis week the Platform team shipped the new login page, finished the database migration, "
    "reviewed three design docs and planned next sprint. We also hit a blocker: the staging cluster is down. "
    "More details below...\n\nThanks",
    json.dumps({
        "facts": {"manager": "Priya (priya.shah@example.com)", "team": "Platform team"},
        "procedure": "Status emails: under 30 words, blockers first.",
        "summary": "Drafted the weekly status email; it was too long and buried the blocker.",
        "outcome": "needs_revision",
    }),
    # run 2: the draft benefits from all three kinds of memory
    "Hi Priya,\n\nBlockers: staging cluster still down (ops ticket open).\n\nDone: login page shipped, "
    "database migration finished.\n\nNext: sprint planning on Monday.\n\nPlatform team",
    json.dumps({"facts": {}, "procedure": "", "summary": "Short status email, blockers first. Accepted.",
                "outcome": "success"}),
]


def indent(text: str) -> str:
    return "\n".join(("    " + line).rstrip() for line in text.splitlines())


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    agent = EmailAgent(llm)

    print(f"RUN 1: {TASK}")
    draft = agent.draft(TASK)
    print(f"  draft: {len(draft.split())} words")
    print(f"  feedback: {FEEDBACK_1}")
    agent.reflect(TASK, draft, FEEDBACK_1)

    print("\nMEMORY AFTER RUN 1")
    m = agent.memory
    print("  semantic:   " + "; ".join(f"{k} = {f.value}" for k, f in m.facts.items()))
    print("  episodic:   " + "; ".join(f"run {e.run} [{e.outcome}] {e.summary}" for e in m.episodes))
    print("  procedural: " + "; ".join(m.procedures))

    print(f"\nRUN 2 (a week later): {TASK}")
    draft = agent.draft(TASK)
    if hasattr(llm, "calls"):
        print("  system prompt the model received:\n" + indent(llm.calls[-1]["system"]))
    print(f"  draft ({len(draft.split())} words):\n" + indent(draft))
    agent.reflect(TASK, draft, "Perfect, thanks.")
    print(f"\n  episodes now: {[(e.run, e.outcome) for e in agent.memory.episodes]}")


if __name__ == "__main__":
    main()
