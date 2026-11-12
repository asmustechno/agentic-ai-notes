# 04 · A simple MCP server

A small notes server built with the official MCP Python SDK. It offers all three server primitives: two **tools** (`search_notes`, `add_note`), two **resources** (`notes://index` and the template `notes://{title}`) and one **prompt** (`weekly_review`). Used in [4.4 Build a simple MCP server](../../docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md).

Written for `mcp==2.3.0`, the SDK's 2.x line, where the high-level server class is `MCPServer` (it was called `FastMCP` in 1.x).

| File | What it is |
| --- | --- |
| `notes_server.py` | The server. `python notes_server.py` serves it over stdio, the way an MCP host launches it |
| `main.py` | A client that connects, lists everything and calls each primitive. No model involved |

## Run it

```bash
cd examples
python 04-mcp-server/main.py            # in-process connection
python 04-mcp-server/main.py --stdio    # starts notes_server.py as a subprocess, like a real host
```

Output (both modes print the same):

```text
Connected to notes 1.0.0 (protocol 2026-07-28)

TOOLS (the model decides when to call these)
  search_notes  [read-only]: Search notes by keyword. Returns every note that contains all the words, as 'title: text'.
    input_schema: {"query": {"description": "One or more words to look for, e.g. 'friday train'.", "title": "Query", "type": "string"}}
  add_note: Save a note under a short title. Saving under an existing title replaces that note.
    input_schema: {"title": {"description": "A short title such as 'dentist'.", "maxLength": 40, "title": "Title", "type": "string"}, "text": {"description": "The full note text.", "title": "Text", "type": "string"}}

RESOURCES (the application decides what to attach)
  notes://index  A list of every note title.
  notes://{title}  The full text of one note.  (template)

PROMPTS (the user picks these, e.g. as a slash command)
  /weekly_review(focus): Review all notes and suggest what to do this week.

CALLS
  tools/call add_note -> Saved note 'dentist'.
  tools/call search_notes -> {'result': ['trip: Train to Lyon on Friday at 09:12, platform 4.', 'dentist: Dentist on Friday at 15:00.']}
  tools/call add_note (bad input) -> is_error=True: Error executing tool add_note: title must not be empty
  resources/read notes://index -> ['dentist', 'groceries', 'trip']
  prompts/get weekly_review -> user message, 205 chars, ending
    'Give me a short plan for this week. Focus on travel.'
```

Notice that the JSON Schema for each tool came from the Python type hints and `Field(...)` descriptions: you never wrote it by hand.

## Try it in the MCP Inspector

The [MCP Inspector](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector) is a browser tool for poking at a server without a model. With Node.js 22.19 or newer, from this folder:

```bash
npx @modelcontextprotocol/inspector python notes_server.py
```

## Test it

```bash
pytest 04-mcp-server
```

The tests use the SDK's in-process connection (`Client(server)`), plus one test that starts the server over stdio.

## Things to try

- Add a `delete_note` tool with `ToolAnnotations(destructive_hint=True)`.
- Serve it over HTTP with `mcp.run(transport="streamable-http")` and connect with `Client("http://127.0.0.1:8000/mcp")`.
- Make `search_notes` return a typed result (a Pydantic model) and look at `structured_content` and `output_schema`.
