"""Project 4 solution: a multi-agent content team.

A researcher (with a search tool), a writer and an editor, coordinated by a
supervisor written in plain code. They share one state object, not one chat:
each agent gets a fresh, focused prompt built from the state.

    research -> write -> review --approved--> publish
                  ^         |
                  +-revise--+   (at most max_rounds drafts, then hand to a human)

    python solution/main.py                                   # offline demo
    python solution/main.py "Topic to write about"            # your topic (use a real model)

Read alongside docs/18-projects/18.4-project-4-multi-agent-content-team.md.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

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
    """Keyword search over the knowledge base (offline stand-in for web search or RAG)."""
    terms = set(re.findall(r"[a-z]+", query.lower())) - {"a", "an", "the", "of", "for", "and", "to", "in", "why", "how"}
    scored = [(len(terms & set(re.findall(r"[a-z]+", f"{n.title} {n.text}".lower()))), n) for n in KNOWLEDGE_BASE]
    return [n for score, n in sorted(scored, key=lambda p: -p[0]) if score][:k]


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
        messages: list[Message] = [user(f"Topic: {state.topic}\nAudience: {state.audience}")]
        found: list[str] = []
        for _ in range(self.max_steps):
            reply = self.llm.chat(messages, system=RESEARCHER_PROMPT, tools=[SEARCH_SPEC])
            messages.append(reply.to_message())
            if not reply.tool_calls:
                state.notes, state.note_ids, state.status = reply.text, found, "researched"
                state.log.append(f"researcher: {len(found)} notes found, {len(CITATION.findall(reply.text))} cited")
                return
            for call in reply.tool_calls:
                notes = search_notes(str(call.arguments.get("query", "")))
                found += [n.id for n in notes if n.id not in found]
                payload = [{"id": n.id, "title": n.title, "text": n.text, "source": n.source} for n in notes]
                messages.append(tool_result(call.id, json.dumps(payload)))
        raise RuntimeError("researcher did not finish within its step limit")


WRITER_PROMPT = (
    "You are a technical writer. Write a short article in Markdown: a '# ' title line, then one or two paragraphs. "
    "Use ONLY the facts in the research notes and keep their [N1]-style citations after each fact. "
    "Stay under the word limit. If editor feedback is given, fix every point."
)


class Writer:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def run(self, state: ContentState) -> None:
        brief = (
            f"Topic: {state.topic}\nAudience: {state.audience}\nWord limit: {state.max_words}\n\n"
            f"Research notes:\n{state.notes}"
        )
        review = state.latest_review()
        if review:  # a revision: show the last draft and everything the editor said
            points = "\n".join(f"- {p}" for p in review.hard_failures + review.feedback)
            brief += f"\n\nYour previous draft:\n{state.draft}\n\nEditor feedback to fix:\n{points}"
        reply = self.llm.chat([user(brief)], system=WRITER_PROMPT)
        state.draft, state.status = reply.text.strip(), "drafted"
        state.round += 1
        state.log.append(f"writer: draft {state.round} ({word_count(state.draft)} words)")


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
    """Rules code can check exactly. Never ask a model to count words."""
    problems = []
    if not state.draft.startswith("# "):
        problems.append("Start with a '# ' title line.")
    if (n := word_count(state.draft)) > state.max_words:
        problems.append(f"Too long: {n} words, the limit is {state.max_words}.")
    cited = set(CITATION.findall(state.draft))
    if not cited:
        problems.append("Cite the research notes, e.g. [N1], after each fact.")
    if unknown := sorted(cited - set(state.note_ids)):
        problems.append(f"These citations are not in the research notes: {', '.join(unknown)}.")
    return problems


def parse_json_object(text: str) -> dict[str, Any] | None:
    """The first {...} in a reply, or None. Models sometimes wrap JSON in prose or code fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


class Editor:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def run(self, state: ContentState) -> Review:
        problems = hard_checks(state)
        prompt = f"Audience: {state.audience}\n\nResearch notes:\n{state.notes}\n\nDraft:\n{state.draft}"
        data = parse_json_object(self.llm.chat([user(prompt)], system=EDITOR_PROMPT).text)
        scores: dict[str, int] = {}
        feedback: list[str] = []
        if data is None:
            feedback = ["(The editor's reply was not valid JSON, so this draft could not be scored.)"]
        else:
            raw_scores = data.get("scores", {})
            scores = {k: int(raw_scores[k]) for k in RUBRIC if isinstance(raw_scores.get(k), (int, float))}
            feedback = [str(f) for f in data.get("feedback", [])]
        approved = not problems and len(scores) == len(RUBRIC) and min(scores.values()) >= PASS_MARK
        review = Review(state.round, scores, problems, feedback, approved)
        state.reviews.append(review)
        verdict = "approved" if approved else "changes requested"
        state.log.append(f"editor: round {state.round} {scores or 'unscored'}, {len(problems)} hard failures -> {verdict}")
        return review


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
    """A fixed pipeline in plain code: research once, then write and review until approved or out of rounds."""
    team.researcher.run(state)
    while True:
        team.writer.run(state)
        if team.editor.run(state).approved:
            state.status = "approved"
            state.log.append("supervisor: approved, ready to publish")
            break
        if state.round >= max_rounds:
            state.status = "needs_human"
            state.log.append(f"supervisor: not approved after {max_rounds} drafts, handing to a human")
            break
        state.log.append("supervisor: sending the draft back to the writer")
    return state


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
    topic = " ".join(sys.argv[1:]) or TOPIC
    llm = get_llm(mock_responses=DEMO_SCRIPT)  # one model plays all three roles here
    state = run_pipeline(ContentState(topic), Team.from_llms(llm))
    print(f"Topic: {state.topic}\n")
    print("\n".join(state.log))
    for review in state.reviews:
        if not review.approved:
            print(f"\nRound {review.round} feedback:")
            print("\n".join(f"  - {p}" for p in review.hard_failures + review.feedback))
    print(f"\nStatus: {state.status} after {state.round} drafts\n")
    print(state.draft)
    sources = sorted({NOTES_BY_ID[i].source for i in set(CITATION.findall(state.draft)) if i in NOTES_BY_ID})
    print("\nSources:\n" + "\n".join(f"  {s}" for s in sources))


if __name__ == "__main__":
    main()
