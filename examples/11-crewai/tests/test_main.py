"""The CrewAI version of the weather agent. Offline, with a scripted BaseLLM subclass.

Skipped unless `crewai` is installed (see ../requirements.txt).
"""

import pytest

pytest.importorskip("crewai")

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def kickoff(reply=None):  # type: ignore[no-untyped-def]
    llm = main.ScriptedLLM(model="scripted", calls=[], **({"reply": reply} if reply else {}))
    main.TOOL_LOG.clear()
    result = main.build_crew(llm).kickoff()
    return result, llm


def test_crew_calls_tools_then_answers() -> None:
    result, llm = kickoff()
    assert result.raw == main.ANSWER
    assert main.TOOL_LOG == [
        'get_weather(\'Paris\') -> {"city": "Paris", "temp_c": 14}',
        'get_weather(\'Rome\') -> {"city": "Rome", "temp_c": 19}',
        "calculator('19 - 14') -> 5",
    ]
    assert len(llm.calls) == 3


def test_role_goal_and_backstory_become_the_system_prompt() -> None:
    _, llm = kickoff()
    system, user = llm.calls[0]["messages"][:2]
    assert system["role"] == "system"
    assert system["content"].startswith("You are Travel weather assistant.")
    assert "Your personal goal is: Compare current temperatures" in system["content"]
    assert main.GOAL in user["content"]  # the task description
    assert "expected criteria for your final answer" in user["content"]  # the task's expected_output


def test_tools_are_sent_as_function_schemas() -> None:
    _, llm = kickoff()
    tools = llm.calls[0]["tools"]
    assert [t["function"]["name"] for t in tools] == ["get_weather", "calculator"]
    assert tools[0]["function"]["parameters"]["required"] == ["city"]


def test_tool_results_go_back_to_the_model() -> None:
    _, llm = kickoff()
    second = llm.calls[1]["messages"]
    assert [m.get("tool_call_id") for m in second if m["role"] == "tool"] == ["call_1", "call_2"]


def test_max_iter_forces_a_final_answer() -> None:
    """A model that never stops calling tools. At max_iter, CrewAI withholds the tools and demands an answer."""

    def always_a_tool(messages):  # type: ignore[no-untyped-def]
        if "MUST give your absolute best final answer" in str(messages[-1].get("content")):
            return "Gave up."
        return [main._tool_call(f"c{len(messages)}", "calculator", {"expression": "1+1"})]

    result, llm = kickoff(always_a_tool)
    assert result.raw == "Gave up."
    assert len(llm.calls) == 6  # max_iter=6
    assert llm.calls[-1]["tools"] is None  # no tools offered on the forced last call


def test_tool_functions_run_directly() -> None:
    assert main.calculator.run(expression="2 * (3 + 4)") == "14"
    assert main.get_weather.run(city="Atlantis") == "Unknown city: Atlantis"
