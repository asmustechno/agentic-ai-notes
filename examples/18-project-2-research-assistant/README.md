# 18 · Project 2: Personal research assistant

A research assistant that searches before it answers, cites every claim, and remembers your preferences between sessions. The full guide, with the spec, milestones and stretch goals, is [18.2 Project 2: Personal research assistant](../../docs/18-projects/18.2-project-2-research-assistant.md).

## The spec in brief

| | |
| --- | --- |
| **Goal** | Answer questions from search results, with source ids the code can check, and adapt to the user across sessions. |
| **Tools** | `search(query)` (pluggable backend: an offline corpus by default), `remember(kind, text)`, `forget(text)` |
| **Memory** | Facts and preferences in a JSON file, recalled into the system prompt at the start of each session |
| **Citations** | The model cites ids like `[S1]`; code maps them to real URLs and flags ids no search returned |
| **Real search** | On Claude, swap in Anthropic's server-side web search tool (`web_search_20260209`) with `RESEARCH_SEARCH=anthropic` |
| **Done when** | `pytest 18-project-2-research-assistant` passes against your code |

## Layout

```text
18-project-2-research-assistant/
├── starter/main.py      ← you build here: runnable skeleton with # TODO markers
├── solution/main.py     ← a complete reference solution
└── tests/test_solution.py
```

## Run it

From `examples/`:

```bash
python 18-project-2-research-assistant/starter/main.py    # tells you what is still missing
python 18-project-2-research-assistant/solution/main.py   # two sessions sharing one memory file, offline
```

Output of the solution (offline, with `MockLLM`; the memory file lives in a temporary folder):

```text
=== Session 1 ===
Recalled from memory: nothing yet
User: Hi! I'm a Python developer and I prefer short answers in bullet points. What is the ReAct pattern?
  step 1: remember({"kind": "preference", "text": "Prefers short answers in bullet points."}) -> Saved preference m1.
  step 1: remember({"kind": "fact", "text": "Is a Python developer."}) -> Saved fact m2.
  step 1: search({"query": "ReAct pattern reasoning acting"}) -> S1 ReAct: Synergizing Reasoning and Act..., S2 Chain-of-Thought Prompting Elicits R..., S3 Generative Agents: Interactive Simul...
  step 2: answer
- ReAct interleaves reasoning with actions such as tool calls [S1].
- The model plans, acts, observes the result and updates its plan [S1].

Sources:
  [S1] ReAct: Synergizing Reasoning and Acting in Language Models - https://arxiv.org/abs/2210.03629

=== Session 2 ===
Recalled from memory: ['Prefers short answers in bullet points.', 'Is a Python developer.']
User: What is the Model Context Protocol?
  step 1: search({"query": "Model Context Protocol"}) -> S1 Introducing the Model Context Protoc..., S2 Model Context Protocol documentation..., S3 ReAct: Synergizing Reasoning and Act...
  step 2: answer
- An open standard from Anthropic (November 2024) for connecting AI assistants to data and tools [S1].
- MCP servers expose tools, resources and prompts to MCP clients [S2].

Sources:
  [S1] Introducing the Model Context Protocol - https://www.anthropic.com/news/model-context-protocol
  [S2] Model Context Protocol documentation - https://modelcontextprotocol.io
```

The run ends by printing the memory file, which holds the two memories saved in session 1.

With a real model, ask your own question. Memory is kept in `~/.agentic-ai-notes/research_memory.json` (override with `MEMORY_FILE`):

```bash
LLM_PROVIDER=anthropic python 18-project-2-research-assistant/solution/main.py "What is Reflexion?"
RESEARCH_SEARCH=anthropic LLM_PROVIDER=anthropic python 18-project-2-research-assistant/solution/main.py "What changed in the latest MCP spec?"
```

Server-side web search is billed per search on top of tokens; see the [web search tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool).

## Test it

```bash
pytest 18-project-2-research-assistant                          # tests the solution
PROJECT_TARGET=starter pytest 18-project-2-research-assistant   # tests your starter code
```

On Windows PowerShell, set the variable first: `$env:PROJECT_TARGET="starter"`.
