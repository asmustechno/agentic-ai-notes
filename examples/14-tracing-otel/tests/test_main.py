"""The agent run becomes a tree of spans with GenAI attributes. Offline, with MockLLM and an in-memory exporter."""

from common import MockLLM
from common.testing import load_example
from opentelemetry.trace import StatusCode

main = load_example(__file__)


def run(script: list, **agent_kwargs):
    provider, memory = main.setup_tracing()  # not global: each test gets its own provider
    llm = MockLLM(script)
    agent = main.TracedAgent(llm=llm, tracer=provider.get_tracer("test"), **agent_kwargs)
    answer = agent.run(main.GOAL, run_id="run-test")
    return answer, memory.get_finished_spans(), llm


def by_name(spans):
    return {s.name: s for s in spans}


def test_one_root_span_with_model_and_tool_children() -> None:
    answer, spans, _ = run(main.SCRIPT)
    assert "16 November 2026" in answer
    names = [s.name for s in spans]  # in the order they finished: children first, the run last
    assert names == [
        "chat mock-model",
        "execute_tool get_order",
        "chat mock-model",
        "execute_tool get_shipping_eta",
        "chat mock-model",
        "invoke_agent order-support",
    ]
    root = by_name(spans)["invoke_agent order-support"]
    assert root.parent is None
    assert all(s.parent.span_id == root.context.span_id for s in spans if s is not root)
    assert len({s.context.trace_id for s in spans}) == 1  # one run = one trace


def test_genai_attributes_on_model_and_tool_spans() -> None:
    _, spans, _ = run(main.SCRIPT)
    chat = next(s for s in spans if s.name.startswith("chat"))
    assert chat.attributes["gen_ai.operation.name"] == "chat"
    assert chat.attributes["gen_ai.provider.name"] == "mock"
    assert chat.attributes["gen_ai.request.model"] == "mock-model"
    assert chat.attributes["gen_ai.usage.input_tokens"] > 0
    assert tuple(chat.attributes["gen_ai.response.finish_reasons"]) == ("tool_use",)
    tool = by_name(spans)["execute_tool get_order"]
    assert tool.attributes["gen_ai.tool.name"] == "get_order"
    assert tool.attributes["gen_ai.tool.call.id"].startswith("call_")
    root = by_name(spans)["invoke_agent order-support"]
    assert root.attributes["app.run.id"] == "run-test"
    assert root.attributes["app.run.outcome"] == "answered"


def test_content_is_not_captured_by_default_but_can_be_opted_in() -> None:
    _, spans, _ = run(main.SCRIPT)
    assert not any("gen_ai.tool.call.arguments" in s.attributes for s in spans)
    assert not any("gen_ai.input.messages" in s.attributes for s in spans)
    _, spans, _ = run(main.SCRIPT, capture_content=True)
    tool = by_name(spans)["execute_tool get_order"]
    assert '"order_id": "1234"' in tool.attributes["gen_ai.tool.call.arguments"]
    assert "ParcelCo" in tool.attributes["gen_ai.tool.call.result"]


def test_failing_tool_is_an_error_span_and_an_is_error_result() -> None:
    script = [MockLLM.tool_call("get_order", {"order_id": "9999"}), "I could not find order 9999."]
    answer, spans, llm = run(script)
    tool = by_name(spans)["execute_tool get_order"]
    assert tool.status.status_code is StatusCode.ERROR
    assert tool.attributes["error.type"] == "KeyError"
    assert any(e.name == "exception" for e in tool.events)
    sent_back = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"][0]
    assert sent_back["is_error"] is True and "KeyError" in sent_back["content"]
    assert "could not find" in answer


def test_step_limit_marks_the_run_as_error() -> None:
    script = [MockLLM.tool_call("get_order", {"order_id": "1234"})] * 3
    answer, spans, _ = run(script, max_steps=3)
    root = by_name(spans)["invoke_agent order-support"]
    assert "step limit" in answer
    assert root.status.status_code is StatusCode.ERROR
    assert root.attributes["app.run.outcome"] == "step_limit"


def test_tree_and_totals() -> None:
    _, spans, _ = run(main.SCRIPT)
    tree = main.span_tree(spans)
    assert tree.splitlines()[0].startswith("invoke_agent order-support")
    assert "└─ chat mock-model" in tree
    totals = main.trace_totals(spans)
    assert totals["model_calls"] == 3 and totals["tool_calls"] == 2
    assert totals["input_tokens"] == sum(s.attributes["gen_ai.usage.input_tokens"] for s in spans if s.name.startswith("chat"))
