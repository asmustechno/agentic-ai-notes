# 11 · Microsoft Agent Framework

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) in Microsoft Agent Framework, the successor to AutoGen and Semantic Kernel: one `Agent` with a chat client, instructions and two plain-function tools. Used in [11.4 Microsoft AutoGen & Agent Framework](../../docs/11-frameworks/11.4-microsoft-autogen-and-agent-framework.md).

Tested with `agent-framework==1.26.0` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Agent Framework has no ready-made fake model, so offline the example builds a tiny chat client from `BaseChatClient` (the documented base class for custom clients) plus the framework's `FunctionInvocationLayer`, which is the part that runs tools and loops. Only the model's replies are scripted.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-agent-framework/.venv
source 11-agent-framework/.venv/bin/activate        # Windows: 11-agent-framework\.venv\Scripts\activate
pip install -r 11-agent-framework/requirements.txt
```

## Run it

```bash
python 11-agent-framework/main.py
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

With a real model: `LLM_PROVIDER=anthropic` (`agent_framework.anthropic.AnthropicClient`) or `LLM_PROVIDER=openai` with `OPENAI_MODEL` (`agent_framework.openai.OpenAIChatClient`). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-agent-framework
```

5 tests: the run and its trace, the instructions and tool schemas sent, both tool results going back in one message, `max_iterations` ending a runaway loop with a tool-free final request, and the tools on their own. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Pass `function_invocation_configuration={"max_iterations": 1}` to `ScriptedChatClient()`. What does the last request look like?
- The `agent-framework` package is large. Try installing only `agent-framework-core` plus `agent-framework-openai` in a fresh environment. Does the example still run offline?
