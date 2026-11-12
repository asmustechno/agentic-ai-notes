"""The LangGraph version of the weather agent. Offline, with a scripted fake chat model.

Skipped unless `langgraph` is installed (see ../requirements.txt).
"""

from typing import Any

import pytest

pytest.importorskip("langgraph")

from langchain.messages import AIMessage, SystemMessage, ToolCall, ToolMessage  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.errors import GraphRecursionError  # noqa: E402

from common.testing import load_example  # noqa: E402

main = load_example(__file__)


class RecordingModel(main.FakeToolCallingModel):
    """The example's fake model, plus a record of every conversation it was sent."""

    calls: list[list[Any]] = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def recording_model() -> RecordingModel:
    model = RecordingModel(messages=main.scripted_model().messages)
    model.calls = []
    return model


def test_graph_loops_through_tools_then_answers() -> None:
    final = main.run(main.build_graph(main.scripted_model()))
    assert final["messages"][-1].text == main.ANSWER
    assert final["llm_calls"] == 3
    assert main.trace(final) == [
        'tool call:   get_weather({"city": "Paris"})',
        'tool call:   get_weather({"city": "Rome"})',
        'tool result: {"city": "Paris", "temp_c": 14}',
        'tool result: {"city": "Rome", "temp_c": 19}',
        'tool call:   calculator({"expression": "19 - 14"})',
        "tool result: 5",
    ]


def test_model_node_sends_instructions_and_tool_results() -> None:
    model = recording_model()
    main.run(main.build_graph(model))
    assert len(model.calls) == 3
    first = model.calls[0]
    assert isinstance(first[0], SystemMessage) and first[0].content == main.INSTRUCTIONS
    tool_msgs = [m for m in model.calls[1] if isinstance(m, ToolMessage)]
    assert [m.tool_call_id for m in tool_msgs] == ["call_1", "call_2"]


def test_graph_shape() -> None:
    graph = main.build_graph(main.scripted_model()).get_graph()
    assert set(graph.nodes) == {"__start__", "llm_call", "tool_node", "__end__"}
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("tool_node", "llm_call") in edges and ("llm_call", "__end__") in edges


def test_recursion_limit_stops_a_runaway_loop() -> None:
    looping = main.FakeToolCallingModel(
        messages=iter(
            [AIMessage(content="", tool_calls=[ToolCall(name="calculator", args={"expression": "1+1"}, id=f"c{i}")]) for i in range(50)]
        )
    )
    with pytest.raises(GraphRecursionError):
        main.run(main.build_graph(looping))


def test_checkpointer_keeps_state_per_thread() -> None:
    graph = main.build_graph(main.scripted_model(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "user-42"}}
    main.run(graph, **config)
    saved = graph.get_state(config).values
    assert saved["messages"][-1].text == main.ANSWER
    assert len(saved["messages"]) == 7  # question, 3 model replies, 3 tool results


def test_tools_have_schemas_from_docstrings() -> None:
    assert main.get_weather.description.startswith("Get the current temperature")
    assert main.get_weather.args["city"]["type"] == "string"
    assert main.calculator.invoke({"expression": "2 * (3 + 4)"}) == "14"
    assert main.get_weather.invoke({"city": "Atlantis"}) == "Unknown city: Atlantis"
