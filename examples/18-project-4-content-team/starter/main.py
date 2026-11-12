"""Project 4 starter: a multi-agent content team.

A researcher (with a search tool), a writer and an editor, coordinated by a
supervisor written in plain code. They share one state object, not one chat.
Fill in every `# TODO`. The file runs as it is and tells you what is missing:

    python starter/main.py

Check your work with the same tests the solution passes (from examples/):

    PROJECT_TARGET=starter pytest 18-project-4-content-team          # macOS/Linux
    $env:PROJECT_TARGET="starter"; pytest 18-project-4-content-team  # Windows PowerShell

Guide: docs/18-projects/18.4-project-4-multi-agent-content-team.md
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402,F401

# --------------------------------------------------------------------------- the knowledge base the researcher can search


@dataclass
class Note:
    id: str
    title: str
    text: str
    source: str


KNOWLEDGE_BASE: list[Note] = [
    Note("N1", "Step limits", "An agent loop should stop after a fixed number of model calls. Without a limit, a confused "
         "model can keep calling tools and run up cost.", "docs/02-the-agent-loop/02.4-stopping-conditions.md"),
    Note("N2", "Cost of long runs", "Every step resends the whole conversation, so the tokens used by a run grow faster "
         "than the number of steps.", "docs/16-cost-and-performance/16.1-token-cost-maths.md"),
    Note("N3", "Stopping gracefully", "When an agent reaches its step limit it should say so and return what it has, "
         "instead of failing silently.", "docs/02-the-agent-loop/02.4-stopping-conditions.md"),
    Note("N4", "Run budgets", "Besides a step limit, production agents often cap tokens, money or wall-clock time per run.",
         "docs/16-cost-and-performance/16.5-budget-limits-per-run.md"),
    Note("N5", "Human handoff", "When an important task hits a limit, hand it to a human with a summary of what was tried.",
         "docs/09-agent-design-patterns/09.6-human-in-the-loop.md"),
    Note("N6", "Prompt caching", "Reusing a cached prompt prefix makes repeated requests cheaper and faster.",
         "docs/16-cost-and-performance/16.2-prompt-caching.md"),
    Note("N7", "Parallel tool calls", "A model can ask for several tool calls in one turn; run them and return all the "
         "results together.", "docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md"),
]
NOTES_BY_ID = {n.id: n for n in KNOWLEDGE_BASE}


def search_notes(query: str, k: int = 3) -> list[Note]:
    """Return up to k notes that share words with the query (title + text), most shared words first; [] if none."""
    # TODO (milestone 1)
    raise NotImplementedError("search_notes (milestone 1)")


# --------------------------------------------------------------------------- shared state


@dataclass
class Review:
    round: int
    scores: dict[str, int]
    hard_failures: list[str]
    feedback: list[str]
    approved: bool


Status = Literal["new", "researched", "drafted", "approved", "needs_human"]


@dataclass
class ContentState:
    """Everything the team knows about one piece of content. Agents read it and write their part."""

    topic: str
    audience: str = "developers who are new to AI agents"
    max_words: int = 120
    notes: str = ""  # the researcher's findings, citing note ids like [N1]
    note_ids: list[str] = field(default_factory=list)  # ids the researcher actually retrieved
    draft: str = ""
    round: int = 0  # how many drafts the writer has produced
    reviews: list[Review] = field(default_factory=list)
    status: Status = "new"
    log: list[str] = field(default_factory=list)

    def latest_review(self) -> Review | None:
        return self.reviews[-1] if self.reviews else None


CITATION = re.compile(r"\[(N\d+)\]")

# --------------------------------------------------------------------------- the three agents

RESEARCHER_PROMPT = (
    "You are a researcher. Use search_notes to find facts for the topic. Search at least once. "
    "Then reply with 3 to 5 bullet points. End every bullet with the id of the note it comes from, like [N1]. "
    "Only use facts from the notes."
)
SEARCH_SPEC: ToolSpec = {
    "name": "search_notes",
    "description": "Search the team's knowledge base. Returns up to 3 notes as JSON, each with an id (cite it), title, text and source.",
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}


class Researcher:
    def __init__(self, llm: LLM, max_steps: int = 4) -> None:
        self.llm, self.max_steps = llm, max_steps

    def run(self, state: ContentState) -> None:
        """A small tool-using loop.

        Start with [user(f"Topic: {state.topic}\\nAudience: {state.audience}")], system=RESEARCHER_PROMPT,
        tools=[SEARCH_SPEC]. Run each search_notes call and return the notes as JSON (id, title, text, source).
        Remember every note id you returned. When the model answers in text: set state.notes, state.note_ids
        and state.status = "researched", and add a "researcher: ..." line to state.log.
        Raise RuntimeError if it does not finish within max_steps.
        """
        # TODO (milestone 2)
        raise NotImplementedError("Researcher.run (milestone 2)")


WRITER_PROMPT = (
    "You are a technical writer. Write a short article in Markdown: a '# ' title line, then one or two paragraphs. "
    "Use ONLY the facts in the research notes and keep their [N1]-style citations after each fact. "
    "Stay under the word limit. If editor feedback is given, fix every point."
)


class Writer:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def run(self, state: ContentState) -> None:
        """One model call with a fresh brief built from the state (no tools).

        The brief has the topic, audience, word limit and state.notes. If there is a latest review, add the
        previous draft and every hard failure and feedback point. Store the reply in state.draft, set
        status "drafted", add 1 to state.round, and log "writer: draft N (W words)".
        """
        # TODO (milestone 3)
        raise NotImplementedError("Writer.run (milestone 3)")


RUBRIC = {
    "accuracy": "Every claim is supported by the research notes; nothing is invented or exaggerated.",
    "clarity": "Short sentences, plain words, one idea per sentence, logical order.",
    "audience_fit": "Right level for the audience: terms explained, no unexplained jargon.",
}
PASS_MARK = 4
EDITOR_PROMPT = (
    "You are a strict editor. Score the draft from 1 to 5 on each rubric criterion:\n"
    + "\n".join(f"- {k}: {v}" for k, v in RUBRIC.items())
    + '\nReply with JSON only: {"scores": {"accuracy": n, "clarity": n, "audience_fit": n}, '
    '"feedback": ["specific, actionable point", ...]}. Give feedback for any score below 4.'
)


def word_count(text: str) -> int:
    """Words in the article, ignoring citation markers like [N1]."""
    return len(CITATION.sub("", text).split())


def hard_checks(state: ContentState) -> list[str]:
    """Problems code can check exactly, as messages for the writer:

    no '# ' title line; more than state.max_words words; no [N..] citations;
    citations that are not in state.note_ids (mention the ids).
    """
    # TODO (milestone 4)
    raise NotImplementedError("hard_checks (milestone 4)")


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Return the first {...} object in text (models sometimes add prose or code fences), or None."""
    # TODO (milestone 4)
    raise NotImplementedError("parse_json_object (milestone 4)")


class Editor:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def run(self, state: ContentState) -> Review:
        """Review the current draft.

        Run hard_checks; ask the model (system=EDITOR_PROMPT) with the audience, notes and draft; parse its JSON.
        Invalid JSON -> no scores, feedback says "not valid JSON". Approved only if there are no hard failures
        and every RUBRIC criterion scored >= PASS_MARK. Append the Review to state.reviews, log it, return it.
        """
        # TODO (milestone 5)
        raise NotImplementedError("Editor.run (milestone 5)")


# --------------------------------------------------------------------------- the supervisor


@dataclass
class Team:
    researcher: Researcher
    writer: Writer
    editor: Editor

    @classmethod
    def from_llms(cls, researcher: LLM, writer: LLM | None = None, editor: LLM | None = None) -> Team:
        """One model for everyone, or a different (cheaper or stronger) model per role."""
        return cls(Researcher(researcher), Writer(writer or researcher), Editor(editor or researcher))


def run_pipeline(state: ContentState, team: Team, *, max_rounds: int = 3) -> ContentState:
    """Research once; then write and review until approved (status "approved") or until
    state.round reaches max_rounds (status "needs_human"). Log each decision as "supervisor: ...",
    including "supervisor: sending the draft back to the writer" and "... handing to a human"."""
    # TODO (milestone 6)
    raise NotImplementedError("run_pipeline (milestone 6)")


# --------------------------------------------------------------------------- demo

TOPIC = "Why AI agents need step limits"
RESEARCH_SCRIPT = [
    MockLLM.tool_calls([("search_notes", {"query": "step limit agent loop"}), ("search_notes", {"query": "cost of long runs"})]),
    "- Without a step limit, a confused model can keep calling tools and run up cost [N1].\n"
    "- Each step resends the whole conversation, so tokens grow faster than the number of steps [N2].\n"
    "- At the limit, an agent should say so and return what it has [N3].\n"
    "- Production agents also cap tokens, money or time per run [N4].",
]
DRAFT_1 = (
    "# Step limits: the most important line of agent code\n\n"
    "Step limits are the single most important safety feature in any agent and make agents ten times cheaper. "
    "An agent calls a model in a loop, and a confused model can keep calling tools forever. "
    "Every step also resends the conversation, so costs climb quickly."
)
REVIEW_1 = json.dumps(
    {
        "scores": {"accuracy": 2, "clarity": 4, "audience_fit": 4},
        "feedback": [
            "'Single most important safety feature' and 'ten times cheaper' are not in the notes: remove them.",
            "Mention what the agent should do when it reaches the limit (N3).",
        ],
    }
)
DRAFT_2 = (
    "# Why AI agents need step limits\n\n"
    "An agent calls a model in a loop. Without a step limit, a confused model can keep calling tools and run up "
    "cost [N1]. Long runs are expensive, because every step resends the whole conversation, so tokens grow faster "
    "than the number of steps [N2].\n\n"
    "When an agent reaches its limit, it should say so and return what it has [N3]. In production, teams often "
    "cap tokens, money or time per run as well [N4]."
)
REVIEW_2 = json.dumps({"scores": {"accuracy": 5, "clarity": 5, "audience_fit": 4}, "feedback": []})
DEMO_SCRIPT = RESEARCH_SCRIPT + [DRAFT_1, REVIEW_1, DRAFT_2, REVIEW_2]



def main() -> None:
    llm = get_llm(mock_responses=DEMO_SCRIPT)  # one model plays all three roles here
    try:
        state = run_pipeline(ContentState(TOPIC), Team.from_llms(llm))
    except NotImplementedError as exc:
        print(f"Not finished yet: {exc}. Open starter/main.py and look for '# TODO'.")
        return
    print("\n".join(state.log))
    print(f"\nStatus: {state.status} after {state.round} drafts\n\n{state.draft}")


if __name__ == "__main__":
    main()
