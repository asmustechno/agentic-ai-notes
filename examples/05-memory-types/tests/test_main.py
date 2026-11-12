"""Episodic, semantic and procedural memory. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def run_two_weeks() -> tuple[MockLLM, object]:
    llm = MockLLM(main.SCRIPT)
    agent = main.EmailAgent(llm)
    draft = agent.draft(main.TASK)
    agent.reflect(main.TASK, draft, main.FEEDBACK_1)
    agent.draft(main.TASK)
    return llm, agent


def test_first_run_has_no_memory_in_the_prompt() -> None:
    llm, _ = run_two_weeks()
    assert llm.calls[0]["system"] == main.BASE


def test_reflection_fills_all_three_stores() -> None:
    _, agent = run_two_weeks()
    m = agent.memory
    assert m.facts["manager"].value == "Priya ([email])"  # PII redacted before storage
    assert m.procedures == ["Status emails: under 30 words, blockers first."]
    assert m.episodes[0].outcome == "needs_revision"


def test_second_run_prompt_contains_procedures_facts_and_episodes() -> None:
    llm, _ = run_two_weeks()
    system = llm.calls[2]["system"]
    assert "<procedures>\n- Status emails: under 30 words, blockers first." in system
    assert "- team: Platform team" in system
    assert "run 1 (needs_revision)" in system
    assert "priya.shah@example.com" not in system


def test_newer_fact_replaces_stale_one_and_forget_removes_it() -> None:
    mem = main.AgentMemory()
    mem.set_fact("Manager", "Priya", run=1, source="chat")
    mem.set_fact("manager", "Tom", run=5, source="chat")
    assert mem.facts["manager"].value == "Tom" and mem.facts["manager"].updated_run == 5
    mem.forget("manager")
    assert "manager" not in mem.build_system("base", "anything")


def test_bad_reflection_json_changes_nothing() -> None:
    agent = main.EmailAgent(MockLLM(["not json"]))
    assert agent.reflect("t", "d", "f") == {}
    assert agent.memory.episodes == [] and agent.memory.facts == {}


def test_only_relevant_episodes_are_recalled() -> None:
    mem = main.AgentMemory()
    mem.episodes += [main.Episode(1, "Book a meeting room", "Booked room 4", "success"),
                     main.Episode(2, "Draft status email", "Too long", "needs_revision")]
    assert [e.run for e in mem.relevant_episodes("Draft the status email")] == [2]


def test_redact() -> None:
    assert main.redact("mail sam@example.org or call +44 20 7946 0958") == "mail [email] or call [phone]"
