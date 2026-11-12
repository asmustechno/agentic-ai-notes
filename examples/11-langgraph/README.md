# 11 · LangGraph

The Paris-vs-Rome weather agent from [1.5](../../docs/01-foundations/01.5-anatomy-of-an-agent.md) as a LangGraph **state graph**: an `llm_call` node, a `tool_node` node and a conditional edge that loops back until the model stops asking for tools. The structure follows the official LangGraph quickstart. Used in [11.2 LangGraph](../../docs/11-frameworks/11.2-langgraph.md).

Tested with `langgraph==1.2.21` (see [`requirements.txt`](requirements.txt) for every pin), Python 3.11, November 2026.

## How it runs offline

Offline, the model is LangChain's `GenericFakeChatModel` with scripted replies, subclassed so `bind_tools` returns the model unchanged (the pattern from LangChain's [unit-testing guide](https://docs.langchain.com/oss/python/langchain/test/unit-testing)). The graph, the state and the tool calls are all real.

## Install

Frameworks pin many packages, so give each example **its own virtual environment**, separate from the shared one for `examples/requirements.txt`. From the `examples/` folder:

```bash
python -m venv 11-langgraph/.venv
source 11-langgraph/.venv/bin/activate        # Windows: 11-langgraph\.venv\Scripts\activate
pip install -r 11-langgraph/requirements.txt
```

## Run it

```bash
python 11-langgraph/main.py
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
Model calls: 3
```

With a real model: `LLM_PROVIDER=anthropic` (uses `langchain-anthropic`) or `LLM_PROVIDER=openai` with `OPENAI_MODEL` (uses `langchain-openai`). Put the variables in `examples/.env` (see `examples/.env.example`); the script loads it.

## Test it

```bash
python -m pytest 11-langgraph
```

6 tests: the run and its trace, what the model node sends (system prompt, tool results), the graph's shape, the recursion limit stopping a runaway loop, a checkpointer saving state per thread, and tool schemas. The main test run (with only `examples/requirements.txt` installed) skips these tests, because each test file starts with `pytest.importorskip`.

## Things to try

- Print `build_graph(scripted_model()).get_graph().draw_mermaid()` and paste the output into a Mermaid viewer.
- Lower `recursion_limit` in `run()` to 3. Which error do you get, and after how many node visits?
- Add a `checkpointer=InMemorySaver()` and call `run()` twice with the same `thread_id`. How many messages are in the saved state after the second run?
