"""Acceptance tests for Project 1. Offline, with MockLLM.

By default they test solution/main.py. Set PROJECT_TARGET=starter to test your own work.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from common import MockLLM, ToolCall
from common.llm import LLMResponse


def load(target: str | None = None) -> ModuleType:
    """Import <project>/<target>/main.py under a unique module name."""
    target = target or os.getenv("PROJECT_TARGET", "solution")
    path = Path(__file__).resolve().parent.parent / target / "main.py"
    name = f"p18_1_weather_{target}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader, f"cannot load {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


app = load()


# --------------------------------------------------------------------------- tools


def test_get_weather_returns_json_for_a_known_city() -> None:
    data = json.loads(app.get_weather("paris"))
    assert data["city"] == "Paris" and data["temp_c"] == 14 and data["condition"] == "cloudy"


def test_get_weather_rejects_unknown_and_empty_cities() -> None:
    with pytest.raises(LookupError, match="Known cities"):
        app.get_weather("Atlantis")
    with pytest.raises(ValueError):
        app.get_weather("  ")


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("19 - 14", "5"), ("(14 + 19) / 2", "16.5"), ("2 ** 10", "1024"), ("-3 + 1", "-2"), ("7 % 3", "1"), ("1 / 3", "0.333333")],
)
def test_calculator_does_arithmetic(expression: str, expected: str) -> None:
    assert app.calculator(expression) == expected


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('echo hi')", "open('secrets.txt')", "x + 1", "9 ** 9 ** 9", "1 +", "True + 1", "1" * 300],
)
def test_calculator_refuses_anything_but_arithmetic(expression: str) -> None:
    with pytest.raises(ValueError):
        app.calculator(expression)


def test_tool_descriptions_are_written() -> None:
    for spec in app.TOOL_SPECS:
        assert len(spec["description"]) > 40, f"describe {spec['name']} properly"
    assert "calculator" in app.SYSTEM_PROMPT and "get_weather" in app.SYSTEM_PROMPT


def test_run_tool_turns_every_failure_into_an_error_result() -> None:
    assert app.run_tool("calculator", {"expression": "2 + 2"}) == ("4", False)
    for name, args in [("teleport", {}), ("calculator", {}), ("calculator", {"expression": "1/0"}), ("get_weather", {"city": "Mars"})]:
        output, is_error = app.run_tool(name, args)
        assert is_error and output.startswith("Error")


# --------------------------------------------------------------------------- the loop


def test_demo_runs_parallel_weather_calls_then_the_calculator() -> None:
    llm = MockLLM(app.DEMO_SCRIPT)
    result = app.run_agent(llm, app.DEMO_QUESTION)
    assert "61.7°F" in result.answer
    assert result.steps == 3 and not result.stopped_by_limit
    # the model got the tool descriptions and the system prompt on every call
    assert all(c["tools"] == app.TOOL_SPECS and c["system"] == app.SYSTEM_PROMPT for c in llm.calls)
    # both weather results went back in the same turn, before the second model call
    tool_msgs = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"]
    assert len(tool_msgs) == 2 and '"temp_c": 19' in tool_msgs[1]["content"]
    assert llm.calls[2]["messages"][-1]["content"] == "61.7"


def test_tool_errors_go_back_to_the_model_with_is_error() -> None:
    llm = MockLLM([MockLLM.tool_call("get_weather", {"city": "Atlantis"}), "I don't know Atlantis."])
    result = app.run_agent(llm, "Weather in Atlantis?")
    last = llm.calls[1]["messages"][-1]
    assert last["role"] == "tool" and last["is_error"] is True and "Unknown city" in last["content"]
    assert result.answer == "I don't know Atlantis."


def test_invalid_json_arguments_are_reported_not_run() -> None:
    bad = LLMResponse(tool_calls=[ToolCall(id="t1", name="calculator", arguments={}, error="Invalid JSON arguments")], stop_reason="tool_use")
    llm = MockLLM([bad, "Sorry."])
    app.run_agent(llm, "2+2?")
    last = llm.calls[1]["messages"][-1]
    assert last["is_error"] is True and "Invalid JSON" in last["content"]


def test_loop_stops_at_the_step_limit() -> None:
    llm = MockLLM([MockLLM.tool_call("calculator", {"expression": "1 + 1"})] * 10)
    result = app.run_agent(llm, "loop forever", max_steps=3)
    assert result.stopped_by_limit and len(llm.calls) == 3
    assert "step limit" in result.answer


# --------------------------------------------------------------------------- optional real API (solution only)


def test_open_meteo_client_parses_responses_without_network() -> None:
    if not hasattr(app, "fetch_open_meteo"):
        pytest.skip("optional stretch goal: fetch_open_meteo")

    def fake_open(url: str, timeout: float) -> io.BytesIO:
        assert timeout > 0
        if "geocoding" in url:
            return io.BytesIO(b'{"results": [{"name": "Paris", "latitude": 48.85, "longitude": 2.35}]}')
        return io.BytesIO(b'{"current": {"temperature_2m": 8.0, "wind_speed_10m": 13.8}}')

    data = json.loads(app.fetch_open_meteo("Paris", opener=fake_open))
    assert data == {"city": "Paris", "temp_c": 8.0, "wind_kph": 13.8, "source": "open-meteo"}
