# 11 · Pydantic AI

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) with Pydantic AI: an `Agent` with instructions, two `@agent.tool_plain` tools, and the model chosen at run time. Used in [11.8 Pydantic AI](../../docs/11-frameworks/11.8-pydantic-ai.md).

Tested with `pydantic-ai-slim==2.68.0` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Offline, the agent uses Pydantic AI's own test models: `FunctionModel` (a Python function plays the model) in `main.py`, and also `TestModel` in the tests. The script sets `PYDANTIC_AI_NO_BANNER=1` to hide the start-up banner.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-pydantic-ai/.venv
source 11-pydantic-ai/.venv/bin/activate        # Windows: 11-pydantic-ai\.venv\Scripts\activate
pip install -r 11-pydantic-ai/requirements.txt
```

## Run it

```bash
python 11-pydantic-ai/main.py
```

Output (offline):

```text
Goal: Is it warmer in Paris or Rome right now, and by how much?

tool call:   get_weather({"city":"Paris"})
tool call:   get_weather({"city":"Rome"})
tool result: {"city": "Paris", "temp_c": 14}
tool result: {"city": "Rome", "temp_c": 19}
tool call:   calculator({"expression":"19 - 14"})
tool result: 5

Answer: Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.
Model requests: 3
```

With a real model: `LLM_PROVIDER=anthropic` (model `anthropic:claude-opus-5-5`, or `ANTHROPIC_MODEL`) or `LLM_PROVIDER=openai` with `OPENAI_MODEL`. Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-pydantic-ai
```

5 tests: the run and its trace, tool schemas built from type hints and docstrings, a bad tool argument sent back to the model for a retry, `UsageLimits` stopping a runaway loop, and `TestModel` calling every tool. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Give the agent `output_type=` a Pydantic model with `warmer_city: str` and `difference_c: float`. What does `result.output` look like now?
- In `scripted_reply`, send `{"town": "Paris"}` instead of `{"city": "Paris"}`. What does the model receive back?
