"""The supervisor delegates through agent-tools, and each agent keeps its own context. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def make_team() -> tuple:
    llms = {name: MockLLM(script) for name, script in main.SCRIPTS.items()}
    supervisor, specialists = main.build_team(llms)
    return supervisor, specialists, llms


def test_supervisor_only_sees_specialists_as_tools() -> None:
    supervisor, _, llms = make_team()
    supervisor.run(main.GOAL)
    names = [t["name"] for t in llms["supervisor"].calls[0]["tools"]]
    assert names == ["ask_flights_agent", "ask_hotels_agent"]  # no raw search tools


def test_specialists_get_only_the_brief_not_the_users_conversation() -> None:
    supervisor, _, llms = make_team()
    supervisor.run(main.GOAL)
    flights_first = llms["flights"].calls[0]["messages"]
    assert flights_first == [{"role": "user", "content": main.FLIGHTS_BRIEF}]
    assert main.GOAL not in str(flights_first)  # context isolation
    assert llms["hotels"].calls[0]["system"] == main.HOTELS_PROMPT


def test_specialist_tool_traffic_stays_out_of_supervisor_context() -> None:
    supervisor, _, llms = make_team()
    answer = supervisor.run(main.GOAL)
    assert "298 EUR" in answer
    final_context = llms["supervisor"].calls[1]["messages"]
    tool_msgs = [m["content"] for m in final_context if m["role"] == "tool"]
    assert tool_msgs == [
        "Cheapest: TagusAir, out 09:25, back 21:05, 148 EUR return.",
        "Casa Alfama: 75 EUR per night, rated 8.7, 150 EUR for 2 nights.",
    ]
    assert "Rio Hostel" not in str(final_context)  # raw search results never reach the supervisor


def test_every_agent_uses_tokens() -> None:
    supervisor, specialists, _ = make_team()
    supervisor.run(main.GOAL)
    for agent in [supervisor, *specialists.values()]:
        assert agent.usage.input_tokens > 0


def test_unknown_tool_is_reported_as_error() -> None:
    llms = {"supervisor": MockLLM([MockLLM.tool_call("search_flights", {}), "ok"]), "flights": MockLLM(), "hotels": MockLLM()}
    supervisor, _ = main.build_team(llms)
    assert supervisor.run("x") == "ok"
    tool_msg = llms["supervisor"].calls[1]["messages"][-1]
    assert tool_msg["is_error"] and "Unknown tool" in tool_msg["content"]


def test_hotel_search_filters_by_price() -> None:
    assert "Hotel Baixa Grande" not in main.search_hotels("Lisbon", "2027-03-12", 2, 80)
