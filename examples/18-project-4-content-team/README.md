# 18 · Project 4: Multi-agent content team

A researcher, a writer and an editor produce a short article together. A supervisor written in plain code runs the pipeline, the editor scores each draft against a rubric and can send it back, and after a fixed number of rounds a human takes over. The full guide, with the spec, milestones and stretch goals, is [18.4 Project 4: Multi-agent content team](../../docs/18-projects/18.4-project-4-multi-agent-content-team.md).

## The spec in brief

| | |
| --- | --- |
| **Goal** | Turn a topic into a short, accurate, cited article with no human help in the normal case. |
| **Agents** | Researcher (tool: `search_notes`), Writer (no tools), Editor (rubric + hard checks in code) |
| **Coordination** | A fixed pipeline: research → write → review → revise, at most `max_rounds` drafts, then `needs_human` |
| **Shared state** | One `ContentState` object. Each agent gets a fresh prompt built from it, never another agent's chat. |
| **Done when** | `pytest 18-project-4-content-team` passes against your code |

## Layout

```text
18-project-4-content-team/
├── starter/main.py      ← you build here: runnable skeleton with # TODO markers
├── solution/main.py     ← a complete reference solution
└── tests/test_solution.py
```

## Run it

From `examples/`:

```bash
python 18-project-4-content-team/starter/main.py    # tells you what is still missing
python 18-project-4-content-team/solution/main.py   # the finished team, offline
```

Output of the solution (offline, with `MockLLM` playing all three roles):

```text
Topic: Why AI agents need step limits

researcher: 4 notes found, 4 cited
writer: draft 1 (55 words)
editor: round 1 {'accuracy': 2, 'clarity': 4, 'audience_fit': 4}, 1 hard failures -> changes requested
supervisor: sending the draft back to the writer
writer: draft 2 (82 words)
editor: round 2 {'accuracy': 5, 'clarity': 5, 'audience_fit': 4}, 0 hard failures -> approved
supervisor: approved, ready to publish

Round 1 feedback:
  - Cite the research notes, e.g. [N1], after each fact.
  - 'Single most important safety feature' and 'ten times cheaper' are not in the notes: remove them.
  - Mention what the agent should do when it reaches the limit (N3).

Status: approved after 2 drafts

# Why AI agents need step limits

An agent calls a model in a loop. Without a step limit, a confused model can keep calling tools and run up cost [N1]. Long runs are expensive, because every step resends the whole conversation, so tokens grow faster than the number of steps [N2].

When an agent reaches its limit, it should say so and return what it has [N3]. In production, teams often cap tokens, money or time per run as well [N4].

Sources:
  docs/02-the-agent-loop/02.4-stopping-conditions.md
  docs/16-cost-and-performance/16.1-token-cost-maths.md
  docs/16-cost-and-performance/16.5-budget-limits-per-run.md
```

The first feedback point came from code (`hard_checks`), the other two from the editor model.

With a real model, pass your own topic:

```bash
LLM_PROVIDER=anthropic python 18-project-4-content-team/solution/main.py "Why agents should ask before risky actions"
```

## Test it

```bash
pytest 18-project-4-content-team                          # tests the solution
PROJECT_TARGET=starter pytest 18-project-4-content-team   # tests your starter code
```

On Windows PowerShell, set the variable first: `$env:PROJECT_TARGET="starter"`.
