"""The blackboard prevents lost updates and enforces views. Offline, with MockLLM."""

import json

from common import MockLLM, user
from common.testing import load_example

main = load_example(__file__)


def run_scenario() -> tuple:
    llms = {name: MockLLM(script) for name, script in main.SCRIPTS.items()}
    board, agents = main.build(llms)
    trace = main.run_interleaved(agents)
    return board, agents, trace, llms


def test_no_update_is_lost() -> None:
    board, agents, _, _ = run_scenario()
    shortlist = board.entries["shortlist"]
    assert shortlist.version == 2
    assert main.VENUE_A in shortlist.value and main.VENUE_B in shortlist.value
    assert all(a.done for a in agents)


def test_stale_write_is_rejected_with_an_explanation() -> None:
    board, _, _, llms = run_scenario()
    assert any(line.startswith("CONFLICT scout_b") for line in board.log)
    conflict_msg = llms["scout_b"].calls[2]["messages"][-1]
    assert conflict_msg["is_error"] and "Version conflict" in conflict_msg["content"]
    assert main.VENUE_A in conflict_msg["content"]  # tells the agent what the other agent wrote


def test_agents_really_interleave() -> None:
    _, _, trace, _ = run_scenario()
    round1 = trace[trace.index("-- round 1") + 1 : trace.index("-- round 2")]
    assert [line.split("]")[0] for line in round1] == ["[scout_a", "[scout_b"]


def test_views_hide_keys_an_agent_may_not_read() -> None:
    _, _, _, llms = run_scenario()
    first_read = json.loads(llms["scout_a"].calls[1]["messages"][-1]["content"])
    assert set(first_read) == {"brief"}  # budget_notes is finance-only
    assert "3800" not in str(llms["scout_a"].calls)


def test_write_permission_is_enforced() -> None:
    board, _ = main.build({"scout_a": MockLLM(), "scout_b": MockLLM()})
    ok, msg = board.write("scout_a", "brief", "Party in Ibiza!", expected_version=1)
    assert not ok and "Permission denied" in msg
    assert board.entries["brief"].value == main.BRIEF


def test_compare_and_set() -> None:
    board, _ = main.build({"scout_a": MockLLM(), "scout_b": MockLLM()})
    assert board.write("scout_a", "shortlist", "x", 0)[0]
    assert not board.write("scout_b", "shortlist", "y", 0)[0]
    assert board.write("scout_b", "shortlist", "x\ny", 1)[0]


def test_scheduler_stops_at_round_limit() -> None:
    forever = [MockLLM.tool_call("read_board")] * 20
    board, agents = main.build({"scout_a": MockLLM(forever), "scout_b": MockLLM(forever)})
    trace = main.run_interleaved(agents, max_rounds=3)
    assert trace.count("-- round 3") == 1 and "-- round 4" not in trace
    assert not any(a.done for a in agents)
    assert agents[0].messages[0] == user("Find one venue in Lisbon.")
