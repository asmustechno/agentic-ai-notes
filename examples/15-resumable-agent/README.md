# 15 · Resumable agent

An agent that saves its state to SQLite after every step, so a run that crashes can be picked up again without repeating model calls or side effects. Uses only the standard library (`sqlite3`). Used in [15.4 State persistence & resumability](../../docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md).

| Part | What it does |
| --- | --- |
| `CheckpointStore` | One row per run: messages (as JSON), step counter, status, answer, resume count. Each save is one transaction |
| `encode_messages()` / `decode_messages()` | Turn the neutral messages (with `ToolCall` objects and Anthropic content blocks) into JSON and back |
| `ResumableAgent.run()` | Load the run if it exists, then decide the next action from the saved state: run pending tools, or call the model |
| `Outbox` | A fake email service that ignores a repeated idempotency key |
| `crash_once_at()` | Raises `SimulatedCrash` at a chosen point, to test every crash window |

## Run it

```bash
cd examples
python 15-resumable-agent/main.py
```

Output (offline, with `MockLLM`):

```text
A) Crash right after send_email's result was saved
  step 1: model -> get_sales (saved)
  step 1: get_sales -> {"orders": 1284, "revenue_gbp": 48210}
  step 2: model -> send_email (saved)
  step 2: send_email -> sent to team@example.com
  CRASH at tool_saved:send_email
  resume run-42 at step 2 (5 messages saved)
  step 3: model -> answer (saved)
  answer: Sent the 2026-W45 report to team@example.com: 1,284 orders and £48,210 revenue.
  emails actually sent: 1

B) Crash after the email went out but BEFORE its result was saved
  step 1: model -> get_sales (saved)
  step 1: get_sales -> {"orders": 1284, "revenue_gbp": 48210}
  step 2: model -> send_email (saved)
  step 2: send_email -> sent to team@example.com
  CRASH at tool_ran:send_email
  resume run-42 at step 2 (4 messages saved)
  step 2: send_email -> already sent (key run-42:call_2)
  step 3: model -> answer (saved)
  answer: Sent the 2026-W45 report to team@example.com: 1,284 orders and £48,210 revenue.
  emails actually sent: 1
```

In **A**, the resumed run skips everything already saved and makes only the final model call. In **B**, the crash hit the one window a checkpoint cannot cover: the email was sent but the result was not saved. The resumed run calls `send_email` again, but with the same idempotency key (`run-42:call_2`, built from saved data), so the email service ignores the repeat.

## Test it

```bash
pytest 15-resumable-agent
```

The tests crash the run at every point in turn and check that exactly one email goes out and no model call is repeated. One test shows the honest cost of a crash just before a reply is saved: one model call is paid for twice, but nothing happens twice.

## Things to try

- Remove the `idempotency_key` check in `Outbox.send`. Which crash point now sends two emails?
- Open the database after a crashed run (`sqlite3 a.db "select step, status from runs"`) and look at what was saved.
- Add a `cancelled` status and an endpoint-like function that sets it. How should `run()` react when it loads a cancelled run?
