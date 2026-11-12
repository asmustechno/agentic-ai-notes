"""Trace an agent run with OpenTelemetry: one span for the run, one per model call, one per tool call.

    python main.py                       # from this folder
    python 14-tracing-otel/main.py       # from examples/
    python 14-tracing-otel/main.py --console   # also print every span as OpenTelemetry JSON

Span names and attributes follow the OpenTelemetry GenAI semantic conventions
(status: Development, so names can still change):

    invoke_agent order-support         gen_ai.operation.name = invoke_agent
      chat <model>                     gen_ai.operation.name = chat, gen_ai.usage.*
      execute_tool get_order           gen_ai.operation.name = execute_tool, gen_ai.tool.*

Read alongside docs/14-observability-and-debugging/14.1-tracing-agent-runs.md
and 14.3-opentelemetry-for-llm-apps.md.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer  # noqa: E402

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- tools (fake shop data)

ORDERS = {"1234": {"status": "shipped", "carrier": "ParcelCo", "tracking_id": "PC-998877"}}
ETAS = {"PC-998877": "2026-11-16"}


def get_order(order_id: str) -> str:
    """Look up an order. Raises KeyError for an unknown order, like a real client library might."""
    return json.dumps(ORDERS[order_id])


def get_shipping_eta(tracking_id: str) -> str:
    """Estimated delivery date for a parcel."""
    return json.dumps({"tracking_id": tracking_id, "eta": ETAS[tracking_id]})


TOOLS: dict[str, tuple[Callable[..., str], ToolSpec]] = {
    "get_order": (
        get_order,
        {
            "name": "get_order",
            "description": "Get status, carrier and tracking ID for an order. order_id is digits only, e.g. '1234'.",
            "input_schema": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    ),
    "get_shipping_eta": (
        get_shipping_eta,
        {
            "name": "get_shipping_eta",
            "description": "Get the estimated delivery date (YYYY-MM-DD) for a tracking ID.",
            "input_schema": {
                "type": "object",
                "properties": {"tracking_id": {"type": "string"}},
                "required": ["tracking_id"],
            },
        },
    ),
}

INSTRUCTIONS = "You are an order-support agent. Use the tools to look things up; never guess dates."
GOAL = "Where is my order 1234 and when will it arrive?"
SCRIPT = [
    MockLLM.tool_call("get_order", {"order_id": "1234"}),
    MockLLM.tool_call("get_shipping_eta", {"tracking_id": "PC-998877"}),
    "Your order 1234 has shipped with ParcelCo (tracking PC-998877). It should arrive on 16 November 2026.",
]

# --------------------------------------------------------------------------- tracing setup


def setup_tracing(*, console: bool = False, set_global: bool = False) -> tuple[TracerProvider, InMemorySpanExporter]:
    """Create a tracer provider that keeps finished spans in memory (and optionally prints them).

    In production you would add a BatchSpanProcessor with an OTLP exporter pointed at your backend.
    `set_global=True` registers the provider for the whole process, so libraries that emit their own
    spans (the Anthropic SDK does) send them to the same place.
    """
    provider = TracerProvider()
    memory = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    if console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    if set_global:
        trace.set_tracer_provider(provider)
    return provider, memory


# --------------------------------------------------------------------------- the traced agent


@dataclass
class TracedAgent:
    """A plain agent loop with a span around the run, each model call and each tool call."""

    llm: LLM
    tracer: Tracer
    name: str = "order-support"
    tools: dict[str, tuple[Callable[..., str], ToolSpec]] = field(default_factory=lambda: dict(TOOLS))
    instructions: str = INSTRUCTIONS
    max_steps: int = 6
    capture_content: bool = False  # opt-in: prompts and tool payloads can hold personal data

    def run(self, goal: str, *, run_id: str | None = None) -> str:
        run_id = run_id or uuid.uuid4().hex[:12]
        with self.tracer.start_as_current_span(f"invoke_agent {self.name}", kind=SpanKind.INTERNAL) as root:
            root.set_attribute("gen_ai.operation.name", "invoke_agent")
            root.set_attribute("gen_ai.agent.name", self.name)
            root.set_attribute("app.run.id", run_id)  # your own correlation ID: put it in your logs too
            messages: list[Message] = [user(goal)]
            specs = [spec for _, spec in self.tools.values()]

            for step in range(1, self.max_steps + 1):
                reply = self._call_model(messages, specs, step)
                messages.append(reply.to_message())
                if not reply.tool_calls:
                    root.set_attribute("app.run.steps", step)
                    root.set_attribute("app.run.outcome", "answered")
                    return reply.text
                for call in reply.tool_calls:
                    messages.append(self._call_tool(call.id, call.name, call.arguments))

            root.set_attribute("app.run.steps", self.max_steps)
            root.set_attribute("app.run.outcome", "step_limit")
            root.set_status(Status(StatusCode.ERROR, "step limit reached"))
            return "I could not finish within the step limit."

    def _call_model(self, messages: list[Message], specs: list[ToolSpec], step: int) -> LLMResponse:
        model = self.llm.model or "unknown"
        with self.tracer.start_as_current_span(f"chat {model}", kind=SpanKind.CLIENT) as span:
            span.set_attribute("gen_ai.operation.name", "chat")
            span.set_attribute("gen_ai.provider.name", self.llm.provider)
            span.set_attribute("gen_ai.request.model", model)
            span.set_attribute("app.step", step)
            if self.capture_content:
                span.set_attribute("gen_ai.input.messages", json.dumps(messages, default=str))
            reply = self.llm.chat(messages, system=self.instructions, tools=specs)
            span.set_attribute("gen_ai.usage.input_tokens", reply.usage.input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", reply.usage.output_tokens)
            span.set_attribute("gen_ai.response.finish_reasons", [reply.stop_reason])
            span.set_attribute("app.tool_calls", len(reply.tool_calls))
            if reply.stop_reason in ("max_tokens", "refusal"):
                span.set_status(Status(StatusCode.ERROR, f"stop_reason={reply.stop_reason}"))
            return reply

    def _call_tool(self, call_id: str, name: str, arguments: dict[str, Any]) -> Message:
        with self.tracer.start_as_current_span(f"execute_tool {name}", kind=SpanKind.INTERNAL) as span:
            span.set_attribute("gen_ai.operation.name", "execute_tool")
            span.set_attribute("gen_ai.tool.name", name)
            span.set_attribute("gen_ai.tool.call.id", call_id)
            span.set_attribute("gen_ai.tool.type", "function")
            if self.capture_content:
                span.set_attribute("gen_ai.tool.call.arguments", json.dumps(arguments))
            try:
                if name not in self.tools:
                    raise LookupError(f"unknown tool {name!r}")
                result = self.tools[name][0](**arguments)
            except Exception as exc:  # the model must hear about the failure, and so must the trace
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("error.type", type(exc).__qualname__)
                return tool_result(call_id, f"Error: {type(exc).__name__}: {exc}", is_error=True)
            span.set_attribute("app.tool.result_chars", len(result))  # size, not content, by default
            if self.capture_content:
                span.set_attribute("gen_ai.tool.call.result", result)
            return tool_result(call_id, result)


# --------------------------------------------------------------------------- printing a trace as a tree


def span_tree(spans: Sequence[ReadableSpan]) -> str:
    """Render finished spans as an indented tree with durations and the most useful attributes."""
    children: dict[int | None, list[ReadableSpan]] = {}
    for s in spans:
        parent = s.parent.span_id if s.parent else None
        children.setdefault(parent, []).append(s)
    for kids in children.values():
        kids.sort(key=lambda s: s.start_time or 0)

    def describe(s: ReadableSpan, indent: int) -> str:
        a = s.attributes or {}
        ms = ((s.end_time or 0) - (s.start_time or 0)) / 1e6
        bits = [f"{s.name:<{34 - indent}} {round(ms, -1):>5.0f} ms"]
        if "gen_ai.usage.input_tokens" in a:
            bits.append(f"in={a['gen_ai.usage.input_tokens']} out={a['gen_ai.usage.output_tokens']}")
            bits.append(f"stop={a['gen_ai.response.finish_reasons'][0]}")
        if "app.tool.result_chars" in a:
            bits.append(f"result={a['app.tool.result_chars']} chars")
        if s.status.status_code is StatusCode.ERROR:
            bits.append(f"ERROR {a.get('error.type', '')}: {s.status.description}".strip())
        if "app.run.outcome" in a:
            bits.append(f"outcome={a['app.run.outcome']} steps={a['app.run.steps']}")
        return "  ".join(bits)

    lines: list[str] = []

    def walk(parent: int | None, prefix: str) -> None:
        kids = children.get(parent, [])
        for i, s in enumerate(kids):
            last = i == len(kids) - 1
            branch = "" if parent is None else ("└─ " if last else "├─ ")
            lines.append(prefix + branch + describe(s, len(prefix + branch)))
            walk(s.context.span_id, prefix + ("" if parent is None else ("   " if last else "│  ")))

    walk(None, "")
    return "\n".join(lines)


def trace_totals(spans: Sequence[ReadableSpan]) -> dict[str, int]:
    """Sum token usage over the model-call spans only (each token counted once)."""
    chats = [s for s in spans if (s.attributes or {}).get("gen_ai.operation.name") == "chat"]
    return {
        "model_calls": len(chats),
        "tool_calls": sum(1 for s in spans if (s.attributes or {}).get("gen_ai.operation.name") == "execute_tool"),
        "input_tokens": sum(int(s.attributes["gen_ai.usage.input_tokens"]) for s in chats),
        "output_tokens": sum(int(s.attributes["gen_ai.usage.output_tokens"]) for s in chats),
    }


# --------------------------------------------------------------------------- demo helpers


class DelayedLLM(LLM):
    """Wrap a model and add a fixed delay, so the offline demo has realistic-looking timings."""

    def __init__(self, inner: LLM, seconds: float) -> None:
        self.inner, self.seconds = inner, seconds
        self.provider, self.model = inner.provider, inner.model

    def chat(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        time.sleep(self.seconds)
        return self.inner.chat(messages, **kwargs)


def slow(fn: Callable[..., str], seconds: float) -> Callable[..., str]:
    """Return `fn` with an added delay (for the demo's timings only)."""

    def wrapper(**kwargs: Any) -> str:
        time.sleep(seconds)
        return fn(**kwargs)

    return wrapper


def main() -> None:
    console = "--console" in sys.argv
    provider, memory = setup_tracing(console=console, set_global=True)
    llm = get_llm(mock_responses=SCRIPT)
    agent = TracedAgent(llm=llm, tracer=provider.get_tracer("agentic-ai-notes.14-tracing-otel"))
    if llm.provider == "mock":  # pretend the model and the tools take realistic amounts of time
        agent.llm = DelayedLLM(llm, 0.3)
        agent.tools = {name: (slow(fn, delay), spec) for (name, (fn, spec)), delay in zip(TOOLS.items(), (0.05, 0.4))}

    print(f"Goal: {GOAL}\n")
    answer = agent.run(GOAL, run_id="run-7f3a2c")
    spans = memory.get_finished_spans()
    print(span_tree(spans))
    print(f"\nTotals: {trace_totals(spans)}")
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
