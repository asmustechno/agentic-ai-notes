# 11 · AutoGen (legacy)

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) in AutoGen AgentChat, with one `AssistantAgent`.

> **AutoGen is archived.** Its README says Microsoft no longer provides fixes or support and points new users to Microsoft Agent Framework. Use [`11-agent-framework`](../11-agent-framework/README.md) for new work. This example is here so you can read existing AutoGen code and compare the two when migrating. Used in [11.4 Microsoft AutoGen & Agent Framework](../../docs/11-frameworks/11.4-microsoft-autogen-and-agent-framework.md).

Tested with `autogen-agentchat==0.7.5` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Offline, the agent uses AutoGen's own `ReplayChatCompletionClient`, which replays a list of scripted model results. `model_info` tells AutoGen the fake model can call functions.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-autogen/.venv
source 11-autogen/.venv/bin/activate        # Windows: 11-autogen\.venv\Scripts\activate
pip install -r 11-autogen/requirements.txt
```

## Run it

```bash
python 11-autogen/main.py
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

With a real model: `LLM_PROVIDER=openai` with `OPENAI_MODEL` (uses `autogen-ext[openai]`). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-autogen
```

4 tests: the run and its trace, the system message and tool schemas sent, the default `max_tool_iterations=1` stopping after one round of tools, and the tools on their own. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Remove `max_tool_iterations=6`. What is the last message of the run now, and why?
- Compare `build_agent` here with the one in `11-agent-framework/main.py`. Which arguments map to which?
