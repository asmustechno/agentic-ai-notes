# 11 · LlamaIndex agents

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) as a LlamaIndex `FunctionAgent`: plain Python functions as tools, a system prompt, and the agent workflow's event stream for the trace. Used in [11.7 LlamaIndex agents](../../docs/11-frameworks/11.7-llamaindex-agents.md).

Tested with `llama-index-core==0.14.25` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Offline, the agent uses LlamaIndex's own `MockFunctionCallingLLM` with a `response_generator` that scripts the model's replies. The `FunctionAgent` workflow, tool schemas and tool calls are real.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-llamaindex/.venv
source 11-llamaindex/.venv/bin/activate        # Windows: 11-llamaindex\.venv\Scripts\activate
pip install -r 11-llamaindex/requirements.txt
```

## Run it

```bash
python 11-llamaindex/main.py
```

Output (offline):

```text
Goal: Is it warmer in Paris or Rome right now, and by how much?

tool call:   get_weather({"city": "Paris"})
tool call:   get_weather({"city": "Rome"})
tool result: {"city": "Paris", "temp_c": 14}
tool result: {"city": "Rome", "temp_c": 19}
tool call:   calculator({"expression": "19 - 14"})
tool result: 5

Answer: Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.
```

With a real model: `LLM_PROVIDER=anthropic` (`llama-index-llms-anthropic`) or `LLM_PROVIDER=openai` with `OPENAI_MODEL` (`llama-index-llms-openai`; it rejects model names it does not know). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-llamaindex
```

4 tests: the run and its event trace, the system prompt, tools and tool results sent to the model, `max_iterations` stopping a runaway loop, and functions becoming tools. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Turn the weather data into a small document index and give the agent a query-engine tool instead of `get_weather`. What changes in the code?
- Run with `max_iterations=1`. What error do you get?
