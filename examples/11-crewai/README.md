# 11 · CrewAI

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) as a one-agent CrewAI **crew**: an `Agent` (role, goal, backstory, tools), a `Task` (description and expected output) and a `Crew` that runs it. Used in [11.3 CrewAI](../../docs/11-frameworks/11.3-crewai.md).

Tested with `crewai==1.15.41` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

CrewAI has no built-in fake model, so offline the example subclasses `BaseLLM`, CrewAI's documented [custom-LLM](https://docs.crewai.com/en/learn/custom-llm) extension point. Its `call()` returns scripted OpenAI-style tool calls, and CrewAI's agent executor runs the tools natively. The script sets `CREWAI_DISABLE_TELEMETRY=true` and `CREWAI_TRACING_ENABLED=false` so the demo sends nothing anywhere.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-crewai/.venv
source 11-crewai/.venv/bin/activate        # Windows: 11-crewai\.venv\Scripts\activate
pip install -r 11-crewai/requirements.txt
```

## Run it

```bash
python 11-crewai/main.py
```

Output (offline):

```text
Goal: Is it warmer in Paris or Rome right now, and by how much?

tool: get_weather('Paris') -> {"city": "Paris", "temp_c": 14}
tool: get_weather('Rome') -> {"city": "Rome", "temp_c": 19}
tool: calculator('19 - 14') -> 5

Answer: Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.
```

With a real model: `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openai` with `OPENAI_MODEL` (CrewAI's `LLM` class with `anthropic/...` or `openai/...` model names). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-crewai
```

6 tests: the run and its tool log, how role/goal/backstory and the task become the prompt, the tool schemas, tool results going back to the model, `max_iter` forcing a final answer, and the tools on their own. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Print `llm.calls[0]["messages"][0]["content"]` after a run. Where did each sentence of the system prompt come from?
- Add a second agent (a "writer" that turns the comparison into a friendly sentence) and a second task. What does the writer receive from the first task?
- Set `max_iter=2`. What happens to the run?
