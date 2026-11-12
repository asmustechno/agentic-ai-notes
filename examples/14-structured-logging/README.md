# 14 · Structured logging for tool calls

JSON log lines for every model call and tool call, with a run ID on every line, redaction of secrets and personal data, and two modes: **prod** (argument names and sizes only) and **debug** (redacted values). Used in [14.2 Logging tool calls](../../docs/14-observability-and-debugging/14.2-logging-tool-calls.md).

## Run it

```bash
cd examples
python 14-structured-logging/main.py
```

Output (offline, with `MockLLM`; timestamps and durations removed so the output is stable):

```text
--- prod logs ---
{"level": "info", "event": "run.start", "run_id": "run-5b1e09", "goal_chars": 75}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 1, "model": "mock-model", "stop_reason": "tool_use", "input_tokens": 26, "output_tokens": 7, "tool_calls": ["find_customer"]}
{"level": "info", "event": "tool.call", "run_id": "run-5b1e09", "step": 1, "tool": "find_customer", "call_id": "call_1", "arg_names": ["email"], "ok": true, "result_chars": 96}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 2, "model": "mock-model", "stop_reason": "tool_use", "input_tokens": 50, "output_tokens": 17, "tool_calls": ["open_ticket"]}
{"level": "info", "event": "tool.call", "run_id": "run-5b1e09", "step": 2, "tool": "open_ticket", "call_id": "call_2", "arg_names": ["priority", "summary"], "ok": true, "result_chars": 43}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 3, "model": "mock-model", "stop_reason": "end_turn", "input_tokens": 61, "output_tokens": 24, "tool_calls": []}
{"level": "info", "event": "run.end", "run_id": "run-5b1e09", "outcome": "answered", "steps": 3}

--- debug logs ---
{"level": "info", "event": "run.start", "run_id": "run-5b1e09", "goal_chars": 75}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 1, "model": "mock-model", "stop_reason": "tool_use", "input_tokens": 26, "output_tokens": 7, "tool_calls": ["find_customer"]}
{"level": "info", "event": "tool.call", "run_id": "run-5b1e09", "step": 1, "tool": "find_customer", "call_id": "call_1", "arg_names": ["email"], "arguments": {"email": "[EMAIL]"}, "ok": true, "result_chars": 96, "result_preview": "{\"email\": \"[EMAIL]\", \"name\": \"Ana\", \"plan\": \"pro\", \"card_number\": \"[CARD]\"}"}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 2, "model": "mock-model", "stop_reason": "tool_use", "input_tokens": 50, "output_tokens": 17, "tool_calls": ["open_ticket"]}
{"level": "info", "event": "tool.call", "run_id": "run-5b1e09", "step": 2, "tool": "open_ticket", "call_id": "call_2", "arg_names": ["priority", "summary"], "arguments": {"summary": "Double charge for [EMAIL]", "priority": "high"}, "ok": true, "result_chars": 43, "result_preview": "{\"ticket_id\": \"T-1042\", \"priority\": \"high\"}"}
{"level": "info", "event": "model.call", "run_id": "run-5b1e09", "step": 3, "model": "mock-model", "stop_reason": "end_turn", "input_tokens": 61, "output_tokens": 24, "tool_calls": []}
{"level": "info", "event": "run.end", "run_id": "run-5b1e09", "outcome": "answered", "steps": 3}

Answer: Thanks Ana. I've opened ticket T-1042 with high priority; billing will refund the duplicate charge.
```

Neither mode ever prints the email address or the card number.

## Test it

```bash
pytest 14-structured-logging
```

The 7 tests check that every line is JSON with the run ID, that prod mode logs sizes and no values, that debug mode redacts, the redactor itself, failed tools logged as warnings, run IDs that stay separate across threads, and that handlers are not duplicated.

## Things to try

- Add a tool with an `api_key` argument and check how it is redacted.
- Swap the order in `logged_tool_call` back to "truncate, then redact" and watch a test catch the leak.
- Ship the JSON lines to a log store and write the query "failed tool calls per tool in the last hour".
