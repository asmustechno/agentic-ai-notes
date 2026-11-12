# 16 · Budget limits per run

A `BudgetTracker` that caps steps, input and output tokens, dollars and seconds for each agent run, checked **before** every model call; a "final step" signal the model can see; and graceful stops that return a partial answer and the reason. Used in [16.5 Budget limits per run](../../docs/16-cost-and-performance/16.5-budget-limits-per-run.md).

The agent is a scripted researcher that wants six search results before answering, but obeys the final-step note. Prices are Claude Opus 5.5's (November 2026); token counts are `MockLLM` estimates.

## Run it

```bash
cd examples
python 16-budget-limits/main.py
```

Output:

```text
no tight limits:
  stopped by: model finished
  usage:  {'steps': 7, 'input_tokens': 5371, 'output_tokens': 91, 'dollars': 0.023304, 'seconds': 0.0}
  answer: From 6 sources: heat pumps cut heating bills in most climates, by roughly a third for typical homes.

max_steps=4:
  note:   step 4: told the model it is the last step
  stopped by: model finished
  usage:  {'steps': 4, 'input_tokens': 1604, 'output_tokens': 55, 'dollars': 0.007516, 'seconds': 0.0}
  answer: From the 3 sources I read: heat pumps cut heating bills in most climates. (Partial answer.)

max_dollars=$0.004:
  stopped by: dollar limit ($0.004)
  usage:  {'steps': 3, 'input_tokens': 811, 'output_tokens': 33, 'dollars': 0.003904, 'seconds': 0.0}
  answer: I stopped before finishing because this run hit its dollar limit ($0.004).
```

With the step cap, the signal let the model finish well on its last step. With the dollar cap, the loop stopped *before* the call that would have gone over.

## Test it

```bash
pytest 16-budget-limits
```

The 7 tests cover a normal finish, the last-step note, a model that ignores the note (the step cap still stops it), the dollar cap, a time cap with an injected fake clock, the tracker's token limits, and the last-step check.

## Things to try

- Combine limits: `Budget(max_steps=6, max_dollars=0.01)`. Which one fires first?
- Add a `max_seconds` limit and use a fake clock to trigger it.
- With a real Claude model, add an Anthropic task budget as well (see the page) and compare how the model paces itself.
