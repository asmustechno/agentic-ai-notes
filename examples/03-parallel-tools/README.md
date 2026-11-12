# 03 · Parallel tool calls

The model asks for three tools in one turn. This example runs them one by one and then at the same time (with a thread pool and with `asyncio`), keeps the results in call order, and shows how they go back to each provider: one user message for Anthropic, one `tool` message per result for OpenAI. Used in [3.5 Parallel tool calls](../../docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md).

## Run it

```bash
cd examples
python 03-parallel-tools/main.py
```

Output (offline; each fake `get_weather` call sleeps 0.3 s, and your timings may differ slightly):

```text
The model asked for 3 tool calls in one turn:
  call_1: get_weather({'city': 'Paris'})
  call_2: get_weather({'city': 'Rome'})
  call_3: get_weather({'city': 'London'})

1) One by one vs at the same time
  sequential: 0.9s
  threads   : 0.3s
  asyncio   : 0.3s

2) How the results go back to each provider
  Anthropic: 3 messages; the last is ONE user message with 3 tool_result blocks:
    {'type': 'tool_result', 'tool_use_id': 'call_1', 'content': '{"city": "Paris", "temp_c": 14}'}
    {'type': 'tool_result', 'tool_use_id': 'call_2', 'content': '{"city": "Rome", "temp_c": 19}'}
    {'type': 'tool_result', 'tool_use_id': 'call_3', 'content': '{"city": "London", "temp_c": 11}'}
  OpenAI: 5 messages; the last 3 are separate role='tool' messages:
    {'role': 'tool', 'tool_call_id': 'call_1', 'content': '{"city": "Paris", "temp_c": 14}'}
    {'role': 'tool', 'tool_call_id': 'call_2', 'content': '{"city": "Rome", "temp_c": 19}'}
    {'role': 'tool', 'tool_call_id': 'call_3', 'content': '{"city": "London", "temp_c": 11}'}

3) The full agent run
  Answer: Rome is the warmest at 19°C (Paris 14°C, London 11°C).
```

## Test it

```bash
pytest 03-parallel-tools
```

One test uses a `threading.Barrier(3)`: it only passes if all three calls are running at the same moment, so it proves concurrency without relying on timings.

## Things to try

- Add `"Atlantis"` to `CALLS`. Do the other two results still arrive?
- Set `max_workers=1` in `run_parallel`. How long does it take now, and why?
- Write an `async def get_weather_async(city)` with `await asyncio.sleep(0.3)` and gather it directly, without `asyncio.to_thread`.
