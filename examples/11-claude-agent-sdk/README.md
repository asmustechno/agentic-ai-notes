# 11 · Claude Agent SDK

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) on the Claude Agent SDK. The SDK runs the Claude Code agent loop; our two tools run in-process as an SDK MCP server, and `tools=[]` removes Claude Code's built-in tools so the agent can only use ours. Used in [11.6 Claude Agent SDK](../../docs/11-frameworks/11.6-claude-agent-sdk.md).

Tested with `claude-agent-sdk==0.2.180` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

**There is no offline model.** The SDK starts the Claude Code runtime (a native binary bundled in the wheel on supported platforms) and needs an API key. So `python main.py` without `ANTHROPIC_API_KEY` explains this and replays the expected tool calls through the real handlers. The offline tests check the tools and options; the end-to-end test is skipped unless you opt in.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-claude-agent-sdk/.venv
source 11-claude-agent-sdk/.venv/bin/activate        # Windows: 11-claude-agent-sdk\.venv\Scripts\activate
pip install -r 11-claude-agent-sdk/requirements.txt
```

## Run it

```bash
python 11-claude-agent-sdk/main.py
```

Output (offline):

```text
Goal: Is it warmer in Paris or Rome right now, and by how much?

ANTHROPIC_API_KEY is not set, so this script does not start a real Claude Code session.
Replaying the expected tool calls locally instead:

tool call:   mcp__travel__get_weather({"city": "Paris"}) -> {"city": "Paris", "temp_c": 14}
tool call:   mcp__travel__get_weather({"city": "Rome"}) -> {"city": "Rome", "temp_c": 19}
tool call:   mcp__travel__calculator({"expression": "19 - 14"}) -> 5
```

With a real model: Set `ANTHROPIC_API_KEY` to run the real agent. The SDK also supports Amazon Bedrock, Google Cloud and Microsoft Foundry through environment variables; see the [quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-claude-agent-sdk
```

6 tests: 5 offline (tool objects and schemas, handler results, error results, options, the local replay) and 1 live test that is **skipped** unless `CLAUDE_AGENT_SDK_LIVE=1` and `ANTHROPIC_API_KEY` are set. The live run calls the real API, which costs money. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Remove `tools=[]` and ask *"Which files are in this folder?"*. Which built-in tool does Claude reach for?
- Lower `max_turns` to 1 and check `ResultMessage.subtype`.
