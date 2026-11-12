# 12 · Regression evals

An eval runner for a small support agent, built to run in CI two ways:

- **On every pull request, offline.** Model replies recorded from a real run ("recordings", sometimes called cassettes) are replayed through `MockLLM`, so the loop, the tools, the state changes and the graders are tested for free and with the same result every time.
- **On a schedule, live.** `--live` calls the real model several times per case and fails the job if the pass rate drops below a threshold or a case that used to pass now fails.

Used in [12.5 Regression testing agents in CI](../../docs/12-evaluation/12.5-regression-testing-in-ci.md).

| File | What it holds |
| --- | --- |
| `main.py` | The agent under test, the grader and the runner (exit code 0 = pass, 1 = fail) |
| `evals/cases.jsonl` | The eval cases: input, expected end state, required words, tags and where each case came from |
| `evals/recorded/*.json` | Recorded model replies per case, stamped with a fingerprint of the prompt and tools |
| `evals/baseline.json` | Which cases passed last time, to spot regressions |
| `tests/test_main.py` | The pytest suite CI runs on every pull request |

## Run it

```bash
cd examples
python 12-regression-evals/main.py
```

Output (offline, replaying recordings):

```text
Running 5 cases x 1 trial(s), replaying recorded replies (prompt 74c6ee222439)

  PASS  refund-damaged     trial 1
  PASS  track-order        trial 1
  PASS  cancel-order       trial 1
  PASS  cancel-shipped     trial 1
  FAIL  refund-over-limit  trial 1  end state {'refunds': {'3333': 900.0}, 'cancelled': [], 'escalated': []} != expected {'refunds': {}, 'cancelled': [], 'escalated': ['3333']}

By tag: cancel 2/2, edge-case 1/1, happy-path 3/3, policy 0/1, refunds 1/2, tracking 1/1
Pass rate: 80% (threshold 80%)
Regressions vs baseline: none
RESULT: PASS
```

`refund-over-limit` is a known failure: the policy "escalate refunds over $500" lives only in the prompt, and the recorded model ignored it. The baseline already lists it as failing, so it is not a *new* regression.

Live, with a real model:

```bash
LLM_PROVIDER=anthropic python 12-regression-evals/main.py --live --trials 3 --threshold 0.8 --out results.json
LLM_PROVIDER=anthropic python 12-regression-evals/main.py --live --record   # refresh the recordings
```

If you change `SYSTEM` or `TOOL_SPECS`, the replay raises `StaleRecording`: the fingerprint no longer matches, so the recordings must be refreshed with `--live --record`.

## Test it

```bash
pytest 12-regression-evals
```

## Things to try

- Fix the known failure for real: make `issue_refund` raise `ToolError` for amounts over $500. Which test now fails, and why is that the right signal to update the recording and the baseline?
- Add a sixth case from an imaginary production bug report, with its own recording.
- Run `python 12-regression-evals/main.py --threshold 0.9`. What exit code do you get?
