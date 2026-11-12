# 02 · A robust agent loop

The loop from [`02-agent-from-scratch`](../02-agent-from-scratch/README.md), hardened. It shows every way a run can stop and every way a step can fail, each with a test. Used in [2.4 Stopping conditions](../../docs/02-the-agent-loop/02.4-stopping-conditions.md) and [2.5 Handling errors in the loop](../../docs/02-the-agent-loop/02.5-handling-errors-in-the-loop.md).

| Stops on | Recovers from |
| --- | --- |
| a final answer | a tool that raises an exception |
| `max_steps` | missing, extra or wrongly typed arguments |
| wall-clock `max_seconds` | an unknown tool name |
| a token budget and a cost budget | arguments that were not valid JSON |
| the same call repeated (no progress) | transient API errors (retry with exponential backoff and jitter) |
| a reply cut off at `max_tokens` (after one retry) | tool output that is too long (truncated) |
| a refusal | |

## Run it

```bash
cd examples
python 02-robust-loop/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: How many US dollars is 250 euros today?

1) A run that hits five different errors and still finishes

   API call failed with a transient error (529 overloaded_error); retry 1/3 after 0.3s
   step 1: get_rate({'base': 'EUR'}) -> ERROR Invalid arguments for get_rate: missing required argument 'quote'. Fix them and call again.
   step 2: get_exchange_rate({'base': 'EUR', 'quote': 'USD'}) -> ERROR Unknown tool 'get_exchange_rate'. Available tools: get_rate, multiply.
   step 3: get_rate({}) -> ERROR Your arguments for get_rate were not valid JSON (Invalid JSON arguments: Expecting ',' delimiter: line 1 column 16 (char 15)). Send the call again.
   step 4: get_rate({'base': 'USD', 'quote': 'EUR'}) -> ERROR get_rate failed: LookupError: no rate for USD->EUR; supported pairs: EUR->USD, GBP->USD
   step 5: get_rate({'base': 'EUR', 'quote': 'USD'}) -> 1.08
   step 6: multiply({'a': 250, 'b': 1.08}) -> 270.0
   step 7: final answer
   stop: final_answer

   Answer: 250 euros is about 270 US dollars today (rate 1.08).
   Tokens: 504 in / 43 out (MockLLM estimates)

2) Why each run stopped

   scenario             stopped_because  steps
   answers              final_answer     1
   keeps calling tools  max_steps        3
   slow tools           timeout          2
   token budget         token_budget     8
   cost budget          cost_budget      2
   repeats itself       no_progress      3
   cut off once         final_answer     2
   cut off twice        max_tokens       2
   refuses              refusal          1
```

The transient error and the "slow tools" timeout are simulated (`FlakyLLM` and `fake_clock`), so the demo runs instantly. The token counts are `MockLLM`'s rough estimates, not real usage.

## Test it

```bash
pytest 02-robust-loop
```

## Things to try

- Change `Limits()` in `main()` to `Limits(max_steps=4)`. Which error does the run never recover from?
- Make the repeated-call check softer: on the first repeat, send an error result such as *"You already called this with the same arguments. Use the earlier result."*, and stop only on the second.
- Add a per-tool timeout by running each tool in a `concurrent.futures.ThreadPoolExecutor` and calling `future.result(timeout=...)`.
