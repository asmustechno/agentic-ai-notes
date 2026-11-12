# 12 · Trajectory metrics

Scores twelve recorded runs of a support agent (three tasks, four trials each) on outcome, path and reliability: final-state checks, keyword matches, strict / in-order / any-order trajectory matching, tool-call precision and recall, steps, cost, latency, and **pass@k versus pass^k**. Used in [12.2 Task, trajectory & tool-use metrics](../../docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md).

| File | What it holds |
| --- | --- |
| `tasks.json` | Each task's input, expected tool calls, expected end state and required answer keywords |
| `recorded_runs.jsonl` | One line per run: the tool calls made, the end state, the answer, tokens and latency |
| `main.py` | The metric functions and a report |

## Run it

```bash
cd examples
python 12-trajectory-metrics/main.py
```

Output (no model is called; the runs are already recorded):

```text
task            #  success strict in-order any-order  prec   rec steps  cost $
refund-damaged  1  yes     yes    yes      yes        1.00  1.00     2  0.0116
refund-damaged  2  yes     no     yes      yes        0.67  1.00     3  0.0174
refund-damaged  3  no      no     no       no         0.50  0.50     2  0.0116
refund-damaged  4  yes     no     yes      yes        0.67  1.00     3  0.0154
track-order     1  yes     yes    yes      yes        1.00  1.00     2  0.0104
track-order     2  yes     yes    yes      yes        1.00  1.00     2  0.0096
track-order     3  no      no     no       no         0.00  0.00     0  0.0040
track-order     4  yes     yes    yes      yes        1.00  1.00     2  0.0104
cancel-order    1  yes     yes    yes      yes        1.00  1.00     2  0.0092
cancel-order    2  yes     no     no       no         1.00  0.50     1  0.0062
cancel-order    3  no      no     no       no         0.00  0.00     2  0.0094
cancel-order    4  no      no     no       no         1.00  0.50     1  0.0078

Task success rate:     8/12 = 67%
Strict trajectory:     5/12
In-order trajectory:   7/12
Mean tool precision:   0.74
Mean tool recall:      0.71
Mean steps per run:    1.83
Mean cost per run:     $0.0103
Latency median / max:  3.4s / 6.0s

Reliability over 4 trials per task (averaged over tasks):
  k   pass@k   pass^k
  1     0.67     0.67
  2     0.94     0.39
  3     1.00     0.17
  4     1.00     0.00
```

Things to notice:

- `refund-damaged` trial 2 made an extra `get_policy` call. Strict matching fails it; in-order matching passes it, and so does the outcome check.
- `cancel-order` trial 2 skipped the lookup but still cancelled the right order: **success with a wrong path**.
- pass@k climbs towards 1 as k grows; pass^k falls towards 0. At k = 1 they are the same number.

## Test it

```bash
pytest 12-trajectory-metrics
```

## Things to try

- Score trajectories by tool name only: pass `with_args=False` in `score_run`. Which runs change?
- Add a fifth trial to `cancel-order` that succeeds. How do pass@4 and pass^4 move?
- Record your own agent's runs with `trajectory_from_messages(messages)` and add them to the JSONL file.
