# 11 · OpenAI Agents SDK

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) with the OpenAI Agents SDK: an `Agent` (instructions, model, tools) run by `Runner`. Used in [11.5 OpenAI Agents SDK](../../docs/11-frameworks/11.5-openai-agents-sdk.md).

Tested with `openai-agents==0.24.0` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Offline, the agent uses the SDK's own test double, `agents.testing.ScriptedModel`, so the real `Runner` loop, tool schemas and tool execution all run; only the model's replies are scripted. Tracing is switched off for offline runs (`RunConfig(tracing_disabled=True)`).

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-openai-agents-sdk/.venv
source 11-openai-agents-sdk/.venv/bin/activate        # Windows: 11-openai-agents-sdk\.venv\Scripts\activate
pip install -r 11-openai-agents-sdk/requirements.txt
```

## Run it

```bash
python 11-openai-agents-sdk/main.py
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
message:     Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.

Answer: Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.
```

With a real model: `LLM_PROVIDER=openai` with `OPENAI_MODEL` (the SDK calls the Responses API). Other providers need one of the SDK's adapters; see the [models guide](https://openai.github.io/openai-agents-python/models/). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-openai-agents-sdk
```

6 tests: the run and its tool outputs, the instructions and tool schemas sent, tool results going back by `call_id`, `max_turns` raising `MaxTurnsExceeded`, a handoff from a triage agent, and the tools on their own. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Add a second agent, `Agent(name="Packing assistant", ...)`, and list it in the first agent's `handoffs`. Script a reply that hands off. What does `result.last_agent` show?
- Run with `max_turns=2`. Which exception do you get?
