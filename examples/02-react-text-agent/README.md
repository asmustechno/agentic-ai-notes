# 02 · ReAct, text format

A ReAct agent written the way the original paper did it: the model writes plain text in a `Thought:` / `Action: tool[input]` format, our code parses the `Action` line, runs the tool, and replies with `Observation: ...`. No native tool calling. Used in [2.2 ReAct explained](../../docs/02-the-agent-loop/02.2-react-explained.md).

## Run it

```bash
cd examples
python 02-react-text-agent/main.py
```

Output (offline, with `MockLLM`):

```text
Question: How many years after the Eiffel Tower was completed did the Empire State Building open?

Thought 1: I need the year the Eiffel Tower was completed.
Action 1: search[Eiffel Tower]
Observation 1: The Eiffel Tower is a wrought-iron tower in Paris. It was completed in 1889 for the World's Fair.
Thought 2: The Eiffel Tower was completed in 1889. Now I need the year the Empire State Building opened.
Action 2: search[Empire State Building]
Observation 2: The Empire State Building is a skyscraper in New York City. It opened in 1931.
Thought 3: It opened in 1931. The gap is 1931 minus 1889.
Action 3: calculate[1931 - 1889]
Observation 3: 42
Thought 4: The difference is 42 years.
Action 4: finish[42 years. The Eiffel Tower was completed in 1889 and the Empire State Building opened in 1931.]

Answer after 4 steps: 42 years. The Eiffel Tower was completed in 1889 and the Empire State Building opened in 1931.
```

In step 1 the scripted model also wrote its own `Observation:` line, with a wrong year (1887). `strip_invented_observation()` cut it off before it reached the history, so the agent used the real result from the `search` tool instead. Real models do this too when nothing stops them.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to watch a real model follow the format.

## Test it

```bash
pytest 02-react-text-agent
```

## Things to try

- Ask a question the encyclopedia cannot answer, such as the height of Big Ben's tower. What does the agent do?
- Remove the line `Never write an Observation yourself.` from `SYSTEM` and run it against a real model. How often does it invent observations?
- Rewrite the agent with native tool calling (see [`02-agent-from-scratch`](../02-agent-from-scratch/README.md)). Which code disappears?
