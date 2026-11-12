# 05 · Summarising memory

Two ways to keep a long conversation inside a token budget, run on the same eight-turn chat. Used in [5.2 Summarisation & context compaction](../../docs/05-memory/05.2-summarisation-and-context-compaction.md).

| Strategy | What happens when the history is over budget |
| --- | --- |
| `TrimmingMemory` | Drop the oldest whole turns (a sliding window) |
| `SummarisingMemory` | Ask the model to fold the oldest turns into a running summary, kept in the system prompt; keep the recent turns word for word |

Both only ever cut the history just before a user message, so a tool call is never separated from its result.

## Run it

```bash
cd examples
python 05-summarising-memory/main.py
```

Output (offline, with `MockLLM`; token counts are rough estimates of about 4 characters per token):

```text
=== TrimmingMemory (budget ~150 tokens) ===
turn 1: sent ~ 38 tokens, 1 msgs
turn 2: sent ~ 69 tokens, 3 msgs
turn 3: sent ~106 tokens, 5 msgs
turn 4: sent ~137 tokens, 7 msgs
turn 5: sent ~116 tokens, 7 msgs  <- trimmed 2 messages
turn 6: sent ~142 tokens, 9 msgs
turn 7: sent ~129 tokens, 9 msgs  <- trimmed 2 messages
turn 8: sent ~134 tokens, 9 msgs  <- trimmed 2 messages
Is '900 euros' still in the context of the last turn? NO

=== SummarisingMemory (budget ~150 tokens) ===
turn 1: sent ~ 38 tokens, 1 msgs
turn 2: sent ~ 69 tokens, 3 msgs
turn 3: sent ~106 tokens, 5 msgs
turn 4: sent ~137 tokens, 7 msgs
turn 5: sent ~109 tokens, 5 msgs  <- summarised 4 messages into 17 tokens
turn 6: sent ~136 tokens, 7 msgs
turn 7: sent ~131 tokens, 5 msgs  <- summarised 4 messages into 47 tokens
turn 8: sent ~141 tokens, 5 msgs  <- summarised 2 messages into 47 tokens
Is '900 euros' still in the context of the last turn? yes
Running summary:
- Budget: 900 euros for four days in Lisbon in May.
- Diet: vegetarian.
- Decided: stay in Alfama (guesthouse about 70 euros a night).
- Day trip: Sintra, train from Rossio, about 40 minutes.
```

Offline, the summaries come from `fake_summary`, a rule-based stand-in. With `LLM_PROVIDER=anthropic` or `openai`, the model writes them from `SUMMARY_REQUEST`.

## Test it

```bash
pytest 05-summarising-memory
```

## Things to try

- Set `keep_recent=2`. How much smaller is each request, and what do you lose?
- Use a cheaper model for the summariser than for the chat (pass a second `LLM` into `SummarisingMemory`).
- Replace `estimate_tokens` with the provider's token counter (see [1.4](../../docs/01-foundations/01.4-how-llms-work.md)).
