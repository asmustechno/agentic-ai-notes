# 15 · Rate limits & fallbacks

Keep an agent answering when a provider is slow, busy or down. Used in [15.5 Rate limits & fallbacks](../../docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md).

| Part | What it does |
| --- | --- |
| `TokenBucket` | Client-side rate limiting: an average rate with short bursts, so you hit fewer 429s |
| `CircuitBreaker` | Stops calling a failing provider (open), then sends one trial call after a cool-down (half-open) |
| `FallbackLLM` | An `LLM` that tries providers in order: skip open circuits, retry retryable errors (honouring `Retry-After`), then fall back. Raises 4xx errors at once |
| `build_real_chain()` | The same chain with real Anthropic and OpenAI clients, SDK retries turned off so they don't multiply |

## Run it

```bash
cd examples
python 15-fallbacks/main.py
```

Output (offline: two `MockLLM`s, a simulated outage and a fake clock, so it runs instantly):

```text
1) Requests during and after an outage of the primary provider
  t=  0.0s  request #1
    anthropic: 529 overloaded_error -> retry in 0.1s (circuit closed)
    anthropic: 529 overloaded_error -> fall back (circuit closed)
    -> [openai] answer to 'question 1'
  t= 10.0s  request #2
    anthropic: 529 overloaded_error -> fall back (circuit open)
    -> [openai] answer to 'question 2'
  t= 20.0s  request #3
    anthropic: circuit open, skipped
    -> [openai] answer to 'question 3'
  t= 40.0s  request #4
    anthropic: circuit half-open, sending one trial call
    anthropic: 529 overloaded_error -> fall back (circuit open)
    -> [openai] answer to 'question 4'
  t= 70.0s  request #5
    anthropic: circuit half-open, sending one trial call
    -> [anthropic] answer to 'question 5'
  t= 90.0s  request #6
    anthropic: 429 rate_limit_error -> retry in 2.0s (circuit closed)
    -> [anthropic] answer to 'question 6'

  served by: ['openai', 'openai', 'openai', 'openai', 'anthropic', 'anthropic']
  calls that reached the primary: 7 (the open circuit saved the rest)

2) Client-side token bucket: 1 request/s, bursts of 3
  request 1 sent at t=0.0s (waited 0.0s)
  request 2 sent at t=0.0s (waited 0.0s)
  request 3 sent at t=0.0s (waited 0.0s)
  request 4 sent at t=1.0s (waited 1.0s)
  request 5 sent at t=2.0s (waited 1.0s)
  request 6 sent at t=3.0s (waited 1.0s)
```

The provider names are labels: both are `MockLLM`s here. The primary is "overloaded" (529) until t=60s and rate-limits once (429 with `Retry-After: 2`) at t=90s.

## Use it with real providers

```python
from main import build_real_chain   # needs ANTHROPIC_API_KEY, OPENAI_API_KEY and OPENAI_MODEL

llm = build_real_chain()            # an LLM like any other: pass it to your agent
reply = llm.chat([{"role": "user", "content": "Hello"}])
print(llm.served_by)
```

Anthropic's **server-side refusal fallback** (already on in `common/llm.py`) is a different thing: it re-runs a request that a safety classifier declined. It does not help with outages or rate limits. The docs page explains both.

## Test it

```bash
pytest 15-fallbacks
```

## Things to try

- Set `failure_threshold=1`. How many calls reach the primary now?
- Should a 429 count as a circuit-breaker failure? Change `FallbackLLM` so it doesn't, and think about when each choice is right.
- Give the primary a token bucket of 0.2 requests per second. What happens to latency, and when would you rather fall back than wait?
