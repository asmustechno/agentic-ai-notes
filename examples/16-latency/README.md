# 16 · Latency: concurrent tools and streaming

Two latency levers, measured with fake tools and a fake stream that simply sleep: running a turn's independent tool calls **concurrently** instead of one after another, and **streaming** so the first words appear long before the answer is finished. Used in [16.4 Latency optimisation](../../docs/16-cost-and-performance/16.4-latency-optimisation.md).

## Run it

```bash
cd examples
python 16-latency/main.py
```

Output (timings are real sleeps, so they can vary by a few hundredths of a second):

```text
1) Three independent tool calls from one model reply
   sequential: 1.6 s   (0.4 + 0.7 + 0.5)
   concurrent: 0.7 s   (the slowest tool, 0.7)

2) Streaming a 60-word answer
   first words on screen after 0.6 s; whole answer after 2.1 s
   without streaming the user stares at nothing for the whole time.
```

Concurrency turns a sum of tool times into the slowest one. Streaming does not shorten the answer, but the user sees it start after the time to first token.

## Test it

```bash
pytest 16-latency
```

The 3 tests check that concurrent execution is faster, that results keep their order and call IDs (so they can all go back to the model in one message), and that the fake stream yields every word.

## Things to try

- Add a fourth tool that takes 1.2 seconds. What are the two timings now?
- Make one tool depend on another's result. Which calls can still run at the same time?
