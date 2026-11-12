# 14 · Debugging walkthrough: a broken agent, step by step

The bug report: *"I asked where my order is. The bot said 'Let me look that up for you.' and stopped."* This example reproduces it from recorded model replies, reads the trace, locates the broken part (the loop), fixes it, and keeps the recording as a regression test. Used in [14.5 Debugging a broken agent](../../docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md).

## Run it

```bash
cd examples
python 14-debugging-walkthrough/main.py
```

Output (offline; the model replies come from `recorded_run.json`):

```text
1) Reproduce with the recorded replies

step 1  model  stop=tool_use  tools=[get_order]  text='Let me look that up for you.'
        end    model finished at step 1

   Answer: Let me look that up for you.

2) Read the trace: automatic checks

   - step 1: model asked for ['get_order'] but no tool ran (loop stopped early?)

3) Locate: model asked for a tool (stop=tool_use) and the loop returned anyway -> part 5, the loop.
   is_final() treats any text as the final answer. Fix: finish only when there are no tool calls.

4) Re-run the same recording with the fix

step 1  model  stop=tool_use  tools=[get_order]  text='Let me look that up for you.'
step 1  tool   get_order({'order_id': '1234'}) -> ok, 72 chars
step 2  model  stop=tool_use  tools=[get_shipping_eta]  text=''
step 2  tool   get_shipping_eta({'tracking_id': 'PC-998877'}) -> ok, 21 chars
step 3  model  stop=end_turn  tools=[-]  text='Your order 1234 has shipped with Parc...'
        end    model finished at step 3

   Answer: Your order 1234 has shipped with ParcelCo (tracking PC-998877) and should arrive on 16 November 2026.
   Problems found: none
```

## What is in the folder

- `main.py`: `RecordingLLM` (wraps any model and saves its replies), `load_recording` (turns a recording into a `MockLLM` script), a tiny `Trace`, `find_problems` (automatic trace checks), and `BrokenAgent` / `Agent` (the bug and the fix).
- `recorded_run.json`: the three replies from the failing run.

To record a run with a real model: `llm = RecordingLLM(get_llm("anthropic"))`, run the agent, then `llm.save(Path("my_run.json"))`. Check recordings for personal data before committing them.

## Test it

```bash
pytest 14-debugging-walkthrough
```

The 6 tests include the regression test (`test_regression_recorded_run_answers_with_the_date`), a check that the bug still reproduces on `BrokenAgent`, a record-and-replay round trip, and the automatic checks for loops and cut-off answers.

## Things to try

- Set the first reply's `"text"` to `""` in `recorded_run.json`. Why does the broken agent now work?
- Write a recording for a different bug: a tool error the loop does not flag with `is_error`.
