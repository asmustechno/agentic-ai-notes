# 14 · Tracing an agent with OpenTelemetry

An order-support agent whose run, model calls and tool calls are each wrapped in an OpenTelemetry span, using the GenAI semantic-convention names (`invoke_agent`, `chat`, `execute_tool`, `gen_ai.*` attributes). Used in [14.1 Tracing agent runs](../../docs/14-observability-and-debugging/14.1-tracing-agent-runs.md) and [14.3 OpenTelemetry for LLM apps](../../docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md).

## Run it

```bash
cd examples
python 14-tracing-otel/main.py
python 14-tracing-otel/main.py --console   # also print every span as OpenTelemetry JSON
```

Output (offline, with `MockLLM`; token counts are estimates and the delays are added for the demo):

```text
Goal: Where is my order 1234 and when will it arrive?

invoke_agent order-support          1360 ms  outcome=answered steps=3
├─ chat mock-model                   300 ms  in=32 out=5  stop=tool_use
├─ execute_tool get_order             50 ms  result=72 chars
├─ chat mock-model                   300 ms  in=50 out=7  stop=tool_use
├─ execute_tool get_shipping_eta     400 ms  result=49 chars
└─ chat mock-model                   300 ms  in=62 out=25  stop=end_turn

Totals: {'model_calls': 3, 'tool_calls': 2, 'input_tokens': 144, 'output_tokens': 37}

Answer: Your order 1234 has shipped with ParcelCo (tracking PC-998877). It should arrive on 16 November 2026.
```

Notice that the input tokens grow on every call (the conversation is resent), and that the slowest single step is a tool, not the model.

## What is in the code

- `setup_tracing()` creates a `TracerProvider` with an `InMemorySpanExporter` (and a `ConsoleSpanExporter` with `--console`). In production, add a `BatchSpanProcessor` with an OTLP exporter for your backend.
- `TracedAgent` is a plain agent loop with a span around the run, each model call and each tool call. Failed tools become error spans (`record_exception`, `error.type`) *and* `is_error` results for the model.
- Prompts and tool payloads are **not** recorded unless you set `capture_content=True`; the conventions mark them as opt-in.
- With `LLM_PROVIDER=anthropic`, the Anthropic SDK adds its own `anthropic.messages.create` spans under each `chat` span, because `main()` registers the provider globally.

## Test it

```bash
pytest 14-tracing-otel
```

The 6 tests check the span tree, the GenAI attributes, that content is opt-in, error spans for failing tools, the step-limit status, and the totals.

## Things to try

- Send the spans to a local Jaeger or Phoenix over OTLP (see [14.4](../../docs/14-observability-and-debugging/14.4-tracing-tools.md)).
- Add `gen_ai.conversation.id` to the root span.
- Make the model call two independent tools at once and run them concurrently. How does the tree change?
