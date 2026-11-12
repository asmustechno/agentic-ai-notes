# 02 · An agent from scratch

A complete tool-using agent in 55 lines of code, with no framework. Used in [2.3 A 50-line agent from scratch](../../docs/02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md).

| File | What it is | Lines of code* |
| --- | --- | --- |
| [`main.py`](main.py) | The agent on the shared wrapper: runs with `MockLLM`, Anthropic or OpenAI | 55 |
| [`raw_anthropic.py`](raw_anthropic.py) | The same agent straight on the `anthropic` SDK | 43 |
| [`raw_openai.py`](raw_openai.py) | The same agent straight on the `openai` SDK (Chat Completions) | 50 |

\*Counted by the test `test_the_agent_really_is_about_50_lines`: lines that hold code, not blank lines, comments or docstrings. The loop itself, `run_agent`, is 18 lines.

## Run it

```bash
cd examples
python 02-agent-from-scratch/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Which port does the web server listen on?

list_files({}) -> 'README.md\nconfig/app.toml\nconfig/db.toml'
read_file({'path': 'config/app.toml'}) -> '[server]\nport = 8080\nworkers = 4'

Answer: The web server listens on port 8080 (set in config/app.toml).
```

The raw versions need a key:

```bash
python 02-agent-from-scratch/raw_anthropic.py   # needs ANTHROPIC_API_KEY
python 02-agent-from-scratch/raw_openai.py      # needs OPENAI_API_KEY and OPENAI_MODEL
```

## Test it

```bash
pytest 02-agent-from-scratch
```

The tests run all three versions offline: `main.py` with `MockLLM`, and the raw versions with small fake clients that record every request.

## Things to try

- Ask *"What port does the database use?"* with a real model. Does it read the right file?
- Make `read_file` raise for every path. What does the model do with the error results?
- Add a `search_files(text)` tool. How many lines does it add?
