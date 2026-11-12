"""The Paris-vs-Rome weather agent from 1.5, rebuilt as a LangGraph graph.

    python main.py                  # from this folder (offline, fake chat model)
    python 11-langgraph/main.py     # from examples/

    LLM_PROVIDER=anthropic python main.py                     # Claude (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=openai OPENAI_MODEL=<model> python main.py   # OpenAI (needs OPENAI_API_KEY)

The graph follows the LangGraph quickstart: an `llm_call` node, a `tool_node`
node, and a conditional edge that loops back until the model stops asking for
tools. Offline, the model is LangChain's `GenericFakeChatModel` with scripted
replies (the pattern from LangChain's unit-testing guide); the graph, state
and tool execution are real. Needs `pip install -r requirements.txt`.

Read alongside docs/11-frameworks/11.2-langgraph.md.
"""

from __future__ import annotations

import ast
import json
import operator
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable
try:
    from dotenv import load_dotenv

    load_dotenv()  # picks up examples/.env (LLM_PROVIDER, API keys) if present
except ImportError:
    pass

from langchain.chat_models import init_chat_model  # noqa: E402
from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolCall, ToolMessage  # noqa: E402
from langchain.tools import tool  # noqa: E402
from langchain_core.language_models import BaseChatModel  # noqa: E402
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.graph.state import CompiledStateGraph  # noqa: E402
from typing_extensions import TypedDict  # noqa: E402

# --------------------------------------------------------------------------- tools

FAKE_WEATHER = {"paris": 14, "rome": 19, "london": 11}
_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


@tool
def get_weather(city: str) -> str:
    """Get the current temperature in °C for one city.

    Args:
        city: City name, e.g. 'Paris'.
    """
    temp = FAKE_WEATHER.get(city.lower())
    return json.dumps({"city": city, "temp_c": temp}) if temp is not None else f"Unknown city: {city}"


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression with + - * / and numbers, e.g. '19 - 14'.

    Args:
        expression: The expression to evaluate.
    """

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        raise ValueError("only numbers and + - * / are allowed")

    try:
        return str(ev(ast.parse(expression, mode="eval").body))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"Error: {exc}"


TOOLS = [get_weather, calculator]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

INSTRUCTIONS = (
    "You are a concise travel assistant. Use get_weather for real temperatures, never guess. "
    "Use calculator for any arithmetic. Answer in one or two sentences."
)
GOAL = "Is it warmer in Paris or Rome right now, and by how much?"
ANSWER = "Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C."

# --------------------------------------------------------------------------- the model


class FakeToolCallingModel(GenericFakeChatModel):
    """A scripted chat model. `bind_tools` returns the model unchanged, as LangChain's testing guide shows."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> FakeToolCallingModel:  # type: ignore[override]
        return self


def scripted_model() -> FakeToolCallingModel:
    """The model's three replies: two parallel tool calls, one calculator call, the answer."""
    return FakeToolCallingModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        ToolCall(name="get_weather", args={"city": "Paris"}, id="call_1"),
                        ToolCall(name="get_weather", args={"city": "Rome"}, id="call_2"),
                    ],
                ),
                AIMessage(content="", tool_calls=[ToolCall(name="calculator", args={"expression": "19 - 14"}, id="call_3")]),
                AIMessage(content=ANSWER),
            ]
        )
    )


def choose_model() -> BaseChatModel:
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        return init_chat_model("anthropic:" + (os.getenv("ANTHROPIC_MODEL") or "claude-opus-5-5"))
    if provider == "openai":
        return init_chat_model("openai:" + os.environ["OPENAI_MODEL"])
    return scripted_model()


# --------------------------------------------------------------------------- the graph


class State(TypedDict):
    """Everything the graph remembers. `operator.add` means new messages are appended, not replaced."""

    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def build_graph(model: BaseChatModel, *, checkpointer: Any = None) -> CompiledStateGraph:
    model_with_tools = model.bind_tools(TOOLS)

    def llm_call(state: State) -> dict[str, Any]:
        """Node: the model reads the conversation and replies, maybe with tool calls."""
        reply = model_with_tools.invoke([SystemMessage(content=INSTRUCTIONS)] + state["messages"])
        return {"messages": [reply], "llm_calls": state.get("llm_calls", 0) + 1}

    def tool_node(state: State) -> dict[str, Any]:
        """Node: run every tool call in the last message and return the results."""
        results = []
        for call in state["messages"][-1].tool_calls:
            output = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
            results.append(ToolMessage(content=output, tool_call_id=call["id"]))
        return {"messages": results}

    def should_continue(state: State) -> Literal["tool_node", "__end__"]:
        """Conditional edge: more tools to run, or finished?"""
        return "tool_node" if state["messages"][-1].tool_calls else END

    builder = StateGraph(State)
    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_node", tool_node)
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder.compile(checkpointer=checkpointer)


def run(graph: CompiledStateGraph, goal: str = GOAL, **config: Any) -> dict[str, Any]:
    # recursion_limit caps the number of node visits: the loop's safety net.
    return graph.invoke({"messages": [HumanMessage(content=goal)], "llm_calls": 0}, {"recursion_limit": 12, **config})


def trace(state: dict[str, Any]) -> list[str]:
    lines = []
    for m in state["messages"]:
        if isinstance(m, AIMessage) and m.tool_calls:
            lines += [f"tool call:   {c['name']}({json.dumps(c['args'])})" for c in m.tool_calls]
        elif isinstance(m, ToolMessage):
            lines.append(f"tool result: {m.content}")
    return lines


def main() -> None:
    final = run(build_graph(choose_model()))
    print(f"Goal: {GOAL}\n")
    print("\n".join(trace(final)))
    print(f"\nAnswer: {final['messages'][-1].text}")
    print(f"Model calls: {final['llm_calls']}")


if __name__ == "__main__":
    main()
