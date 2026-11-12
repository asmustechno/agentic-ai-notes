# 16 · Prompt caching: request layout

Builds the same 4-call agent run two ways, a **naive** layout (timestamp and customer name at the top of the system prompt) and a **cache-friendly** one (sorted tools, frozen system prompt with a breakpoint, per-run details in the first user message, automatic caching for the conversation), and feeds both into a small simulation of a prefix cache. Used in [16.2 Prompt caching](../../docs/16-cost-and-performance/16.2-prompt-caching.md).

The simulation only illustrates the rules: block-level prefix hashes, a 512-token minimum (Claude Opus 5.5), a 20-block lookback, and a 5-minute cache that never expires during the run. Token counts are estimates (~4 characters per token). With a real model, read `usage.cache_read_input_tokens` and `usage.cache_creation_input_tokens` from each response instead.

## Run it

```bash
cd examples
python 16-prompt-caching-layout/main.py
```

Output:

```text
call   layout   input  cache_write  cache_read
   1   naive       23         3560           0
   2   naive       95         3560           0
   3   naive      154         3560           0
   4   naive      219         3560           0
       why no reads? first divergence between requests 1 and 2: block 3: '{"text": "Current time: 2026-11-13T09:30:00. Customer: Ana.\\n\\nYou are' != '{"text": "Current time: 2026-11-13T09:30:07. Customer: Ana.\\n\\nYou are'
   1   cached       0         3589           0
   2   cached       0           72        3589
   3   cached       0           59        3661
   4   cached       0           65        3720

Run cost on Claude Opus 5.5 (simulated tokens): no caching $0.0601, naive layout $0.0743, cache-friendly layout $0.0222
Saving from the layout alone: 63%
```

The naive layout costs *more* than no caching: it pays the write premium on every call and never reads. `first_divergence` finds the culprit by diffing two consecutive requests.

## What is in the code

- `build_request_naive` and `build_request_cached`: the two layouts, as Anthropic Messages API parameters (the cached one is ready to pass to `client.messages.create(**request)`).
- `SimulatedCache`: a toy prefix cache that reports reads, writes and uncached tokens like the API's usage fields.
- `first_divergence`: the "diff two payloads" technique for finding a silent cache invalidator.

## Test it

```bash
pytest 16-prompt-caching-layout
```

The 6 tests check the layout (sorted tools, frozen system, breakpoints), that consecutive requests share their prefix, the healthy read-everything-write-a-little pattern, that the naive layout costs more than no caching, the minimum-length rule, and the cache prices.

## Things to try

- Shuffle the tools on every call in `build_request_cached`. What happens to the reads?
- Raise `MIN_CACHEABLE` to 4,096 (the minimum on some older Claude models) and shorten `POLICY`. When does caching stop?
