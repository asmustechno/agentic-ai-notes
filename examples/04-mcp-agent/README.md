# 04 · An agent that uses MCP tools

An ordinary agent loop whose tools come from an MCP server: the notes server from [`04-mcp-server`](../04-mcp-server/README.md). Used in [4.5 Connect MCP to an agent](../../docs/04-model-context-protocol/04.5-connect-mcp-to-an-agent.md) and [4.6 Security for MCP servers](../../docs/04-model-context-protocol/04.6-mcp-security.md).

What the code does:

1. Opens an MCP client session (`async with Client(...)`).
2. Calls `tools/list` and converts each MCP tool to the wrapper's neutral `{"name", "description", "input_schema"}` (`to_tool_spec`).
3. Runs the usual loop: the model asks for a tool, the agent forwards it with `tools/call`, and the result goes back as a `tool_result`, with `is_error` carried over.
4. Optionally exposes only an allowlist of the server's tools (`allowed_tools`), and refuses any other call.
5. Optionally refuses tools whose definition changed since a human approved them (`pinned`, a dict of `fingerprint()` hashes): a defence against "rug pulls", see [4.6](../../docs/04-model-context-protocol/04.6-mcp-security.md).

## Run it

```bash
cd examples
python 04-mcp-agent/main.py            # launches ../04-mcp-server/notes_server.py over stdio
python 04-mcp-agent/main.py --inproc   # in-process connection instead
```

Output (offline, with `MockLLM` as the model and the real notes server):

```text
Goal: Remember that my dentist appointment is on Friday at 15:00. Then tell me everything I have on Friday.

tools/list -> ['search_notes', 'add_note']; exposing ['search_notes', 'add_note']
step 1: tools/call add_note({'title': 'dentist', 'text': 'Dentist appointment on Friday at 15:00.'}) -> "Saved note 'dentist'."
step 2: tools/call search_notes({'query': 'friday'}) -> 'trip: Train to Lyon on Friday at 09:12, platform 4.\ndentist: Dentist appointment on Friday at 15:00.'
step 3: answer

Answer: Saved. On Friday you have: Train to Lyon on Friday at 09:12, platform 4; Dentist appointment on Friday at 15:00.
```

The model's replies are scripted, but the tool results are real: they come from the server process. Set `LLM_PROVIDER=anthropic` or `openai` to let a real model choose the calls.

## Test it

```bash
pytest 04-mcp-agent
```

The tests connect to the server in-process with the SDK's `Client(server)`, so they need no subprocess, network or API key.

## Things to try

- Pass `allowed_tools={"search_notes"}` to `run(...)` and watch the `add_note` call get refused.
- Give `to_tool_spec` a prefix such as `"notes__"` so tools from two servers can't collide. What else must change in `MCPAgent.run` for calls to still reach the server?
- Connect a second MCP server and merge both tool lists.
