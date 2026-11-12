# 15 · Retries & idempotency

How to retry without doing things twice. Used in [15.3 Queues, retries & idempotency](../../docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md).

| Part | What it shows |
| --- | --- |
| `is_retryable()` | Retry timeouts, 408, 409, 429 and 5xx (including Anthropic's 529). Never retry 400, 401, 403, 404 |
| `backoff_delay()`, `retry()` | Exponential backoff with "full jitter", capped, honouring `Retry-After` |
| `FlakyPaymentsAPI` | A fake refunds API that loses a *response* after the refund was made, and accepts an idempotency key |
| `InMemoryQueue`, `run_worker()` | At-least-once delivery: redelivery after a crash, and a dead-letter queue (DLQ) |
| `run_refund_agent()` | An agent whose side-effecting tool builds its idempotency key from the **job id**, so a redelivered job is safe |

## Run it

```bash
cd examples
python 15-retries-idempotency/main.py
```

Output (offline, with `MockLLM`, a seeded random generator and a fake `sleep`):

```text
1) Backoff schedule, base 0.5s, cap 30s
   no jitter:    0.50   1.00   2.00   4.00   8.00  16.00
   full jitter:  0.16   0.15   1.30   0.29   4.29   5.85

2) Refund through a network that loses the first response
  no idempotency key:
    attempt 1 failed (TimeoutError: response lost on the way back); retrying in 0.03s
    refunds actually made: 2
  with idempotency key:
    attempt 1 failed (TimeoutError: response lost on the way back); retrying in 0.25s
    refunds actually made: 1

3) A queue of agent jobs: one worker crash, one bad order
  deliver job-1 (delivery 1)
  nack    job-1: WorkerCrash: worker died after the work, before the ack -> requeued
  deliver job-2 (delivery 1)
  nack    job-2: APIError: 400 invalid order id 'B-9' -> dead-lettered
  deliver job-1 (delivery 2)
  ack     job-1: Done. Tool said: {'refund_id': 're_1', 'order_id': 'A-1001', 'amount': 20.0}

  refunds actually made: 1  (job-1 ran twice, refunded once)
  dead-letter queue: [('job-2', "APIError: 400 invalid order id 'B-9'")]
```

Notice three things:

- Without a key, a lost response plus a retry refunds the customer **twice**.
- `job-1` ran twice (the worker "crashed" before acking), but the refund happened once, because both runs sent the same key.
- `job-2` failed with a 400. That will never succeed, so it went straight to the DLQ instead of being retried three times.

## Test it

```bash
pytest 15-retries-idempotency
```

## Things to try

- In `run_refund_agent`, build the key from `call.id` instead of `job.id`. Which test fails, and why?
- Change the backoff to "no jitter" and imagine 1,000 clients that all failed at the same moment. When do they all retry?
- Make `FlakyPaymentsAPI` return a 503 three times in a row. How many deliveries does the job get before it is dead-lettered?
