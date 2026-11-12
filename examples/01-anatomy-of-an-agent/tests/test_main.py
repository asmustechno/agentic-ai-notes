"""The five parts of the agent each do their job. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_agent_runs_parallel_tools_then_answers() -> None:
    llm = MockLLM(main.SCRIPT)
    agent = main.build_agent(llm)
    answer = agent.run(main.GOAL)
    assert "Rome is warmer" in answer
    assert len(llm.calls) == 3
    assert agent.log[0].startswith("step 1: get_weather")
    assert agent.log[1].startswith("step 1: get_weather")  # two tools in one step
    assert agent.log[2] == "step 2: calculator({'expression': '19 - 14'}) -> 5"


def test_instructions_and_long_term_memory_go_in_the_system_prompt() -> None:
    llm = MockLLM(["ok"])
    main.build_agent(llm).run("hi")
    system = llm.calls[0]["system"]
    assert system.startswith("You are a concise travel assistant")
    assert "Prefers temperatures in Celsius." in system


def test_tools_are_described_to_the_model() -> None:
    llm = MockLLM(["ok"])
    main.build_agent(llm).run("hi")
    assert [t["name"] for t in llm.calls[0]["tools"]] == ["get_weather", "calculator"]


def test_short_term_memory_carries_tool_results() -> None:
    llm = MockLLM(main.SCRIPT)
    main.build_agent(llm).run(main.GOAL)
    second_call = llm.calls[1]["messages"]
    tool_msgs = [m for m in second_call if m["role"] == "tool"]
    assert len(tool_msgs) == 2 and '"temp_c": 19' in tool_msgs[1]["content"]


def test_loop_stops_at_step_limit() -> None:
    llm = MockLLM([MockLLM.tool_call("calculator", {"expression": "1+1"})] * 10)
    agent = main.build_agent(llm)
    agent.max_steps = 2
    assert "step limit" in agent.run("loop forever")
    assert len(llm.calls) == 2


def test_calculator_is_safe() -> None:
    assert main.calculator("19 - 14") == "5"
    assert main.calculator("2 * (3 + 4)") == "14"
    assert main.calculator("-3 + 1") == "-2"
    assert main.calculator("1 / 0").startswith("Error")
    assert main.calculator("__import__('os')").startswith("Error")


def test_unknown_city() -> None:
    assert main.get_weather("Atlantis") == "Unknown city: Atlantis"
