"""Acceptance tests for Project 4. Offline: one MockLLM per role, so each agent's calls can be checked.

By default they test solution/main.py. Set PROJECT_TARGET=starter to test your own work.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

from common import MockLLM


def load(target: str | None = None) -> ModuleType:
    """Import <project>/<target>/main.py under a unique module name."""
    target = target or os.getenv("PROJECT_TARGET", "solution")
    path = Path(__file__).resolve().parent.parent / target / "main.py"
    name = f"p18_4_content_team_{target}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader, f"cannot load {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


app = load()
GOOD = json.dumps({"scores": {"accuracy": 5, "clarity": 4, "audience_fit": 4}, "feedback": []})
POOR = json.dumps({"scores": {"accuracy": 3, "clarity": 4, "audience_fit": 4}, "feedback": ["Be more precise."]})


def make_team(writer_script: list, editor_script: list) -> tuple:
    researcher, writer, editor = MockLLM(app.RESEARCH_SCRIPT), MockLLM(writer_script), MockLLM(editor_script)
    return app.Team.from_llms(researcher, writer, editor), researcher, writer, editor


def test_search_notes() -> None:
    ids = [n.id for n in app.search_notes("step limit agent loop")]
    assert ids[0] == "N1" and len(ids) <= 3
    assert app.search_notes("zebra") == []


def test_demo_needs_one_revision_then_is_approved() -> None:
    team, researcher, writer, editor = make_team([app.DRAFT_1, app.DRAFT_2], [app.REVIEW_1, app.REVIEW_2])
    state = app.run_pipeline(app.ContentState(app.TOPIC), team)
    assert state.status == "approved" and state.round == 2
    assert [r.approved for r in state.reviews] == [False, True]
    assert state.draft == app.DRAFT_2
    assert (len(researcher.calls), len(writer.calls), len(editor.calls)) == (2, 2, 2)


def test_agents_share_state_not_chat_history() -> None:
    team, researcher, writer, editor = make_team([app.DRAFT_1, app.DRAFT_2], [app.REVIEW_1, app.REVIEW_2])
    state = app.run_pipeline(app.ContentState(app.TOPIC), team)
    first_brief = writer.calls[0]["messages"]
    assert len(first_brief) == 1  # a fresh, single-message context, not the researcher's conversation
    assert state.notes in first_brief[0]["content"]
    revision = writer.calls[1]["messages"][0]["content"]
    assert app.DRAFT_1 in revision and "ten times cheaper" in revision  # previous draft + editor feedback
    assert "Cite the research notes" in revision  # hard-check failures are passed on too
    assert app.DRAFT_2 in editor.calls[1]["messages"][0]["content"]
    assert researcher.calls[0]["tools"][0]["name"] == "search_notes" and writer.calls[0]["tools"] is None


def test_hard_checks_catch_what_models_are_bad_at() -> None:
    state = app.ContentState("t", max_words=10, note_ids=["N1"])
    state.draft = "No title here, and far too many words for the tiny limit we set [N1] [N9]."
    problems = " ".join(app.hard_checks(state))
    assert "title" in problems and "Too long" in problems and "N9" in problems
    state.draft = "# Title\n\nShort and cited [N1]."
    assert app.hard_checks(state) == []
    assert app.word_count("Two words [N1]") == 2


def test_rounds_are_bounded_and_then_a_human_takes_over() -> None:
    team, _, writer, editor = make_team([app.DRAFT_2] * 5, [POOR] * 5)
    state = app.run_pipeline(app.ContentState(app.TOPIC), team, max_rounds=3)
    assert state.status == "needs_human" and state.round == 3
    assert len(writer.calls) == 3 and len(editor.calls) == 3
    assert "handing to a human" in state.log[-1]


def test_editor_handles_invalid_json_and_json_in_prose() -> None:
    assert app.parse_json_object('Sure! ```json\n{"scores": {"accuracy": 5}}\n```') == {"scores": {"accuracy": 5}}
    assert app.parse_json_object("I liked it.") is None
    team, _, _, _ = make_team([app.DRAFT_2, app.DRAFT_2], ["Looks great to me!", GOOD])
    state = app.run_pipeline(app.ContentState(app.TOPIC), team)
    assert state.reviews[0].approved is False and "not valid JSON" in state.reviews[0].feedback[0]
    assert state.status == "approved" and state.round == 2


def test_approval_needs_every_score_at_the_pass_mark_and_no_hard_failures() -> None:
    team, _, _, _ = make_team([app.DRAFT_1, app.DRAFT_2], [GOOD, GOOD])  # editor model likes draft 1...
    state = app.run_pipeline(app.ContentState(app.TOPIC), team)
    assert state.reviews[0].approved is False  # ...but draft 1 has no citations, so code says no
    partial = json.dumps({"scores": {"accuracy": 5}, "feedback": []})
    team, _, _, _ = make_team([app.DRAFT_2, app.DRAFT_2], [partial, GOOD])
    assert app.run_pipeline(app.ContentState(app.TOPIC), team).reviews[0].approved is False


def test_log_records_every_handoff() -> None:
    team, *_ = make_team([app.DRAFT_1, app.DRAFT_2], [app.REVIEW_1, app.REVIEW_2])
    log = app.run_pipeline(app.ContentState(app.TOPIC), team).log
    roles = [line.split(":")[0] for line in log]
    assert roles == ["researcher", "writer", "editor", "supervisor", "writer", "editor", "supervisor"]
