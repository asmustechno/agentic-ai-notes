# 09 · Parallelisation (sectioning & voting)

Sectioning: three focused code reviews (security, performance, readability) run at the same time with `ThreadPoolExecutor`. Voting: the same SQL-injection question is asked five times with reworded prompts and decided by a threshold. Used in [9.3 Parallelisation](../../docs/09-agent-design-patterns/09.3-parallelisation.md).

## Run it

```bash
cd examples
python 09-parallelisation/main.py
```

Output (offline, with `MockLLM`):

```text
SECTIONING: three focused reviews of the same code
  [security] - SQL injection: `name` is put straight into the query. Use a parameterised query.
  [performance] - Fetches every column and filters in Python. Select only needed columns and let SQL filter.
  [readability] - Returns None silently when no user matches. Say so in a docstring or raise an error.
  time: sequential 1.5s, parallel 0.5s

VOTING: 'is this SQL injection?' asked 5 times, flag at 3 or more YES
  YES 3, NO 1, abstain 1 -> flagged: True
```

Each mock reply sleeps 0.5 s to stand in for network time, so you can see the speed-up; timings vary a little between runs. With a real model, `main()` runs the three reviews twice (one after another, then in parallel) to compare times, so it makes 11 calls.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 09-parallelisation
```

## Things to try

- Change `threshold` to 4. Is the code still flagged?
- Make one aspect's call raise an exception. What does `sectioned_review` return for it?
- Set `max_workers=1` in `run_parallel`. How long does the parallel version take now?
