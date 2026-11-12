# 05 · Vector memory

Long-term memory that survives between conversations: facts are stored as vectors, saved to disk, and recalled by similarity through two tools, `remember` and `recall`. Used in [5.3 Vector memory](../../docs/05-memory/05.3-vector-memory.md).

> **The embedder here is a toy.** `HashingEmbedder` turns text into a bag of words hashed into 1,024 slots. It runs offline with no downloads, but it only matches *shared words*. Real systems use an embedding model. `OpenAIEmbedder` in `main.py` shows one (it needs `OPENAI_API_KEY` and `OPENAI_EMBEDDING_MODEL`); Anthropic does not offer its own embedding model and its docs point to providers such as Voyage AI.

## Run it

```bash
cd examples
python 05-vector-memory/main.py
```

Output (offline, with `MockLLM`):

```text
SESSION 1: Please remember: my daughter Mia is allergic to peanuts. Also, I always prefer window seats on flights.
  answer: Got it. I'll remember both.
  remember({'fact': "The user's daughter Mia is allergic to peanuts."}) -> 'Saved memory #2.'
  remember({'fact': 'The user prefers window seats on flights.'}) -> 'Saved memory #3.'
  saved 3 memories to agentic-ai-notes-vector-memory.json

SESSION 2 (new conversation, memory loaded from disk): Find me a flight to Oslo next week, and suggest a snack for Mia for the trip.
  answer: I'll look for flights to Oslo with a window seat, and pack a peanut-free snack for Mia.
  recall({'query': 'flight seat preference'}) -> '[0.58] The user prefers window seats on flights.'
  recall({'query': 'Mia snack'}) -> "[0.35] The user's daughter Mia is allergic to peanuts."

WHERE BAG-OF-WORDS FAILS (scores against every memory)
  'window seat': #3=0.71, #1=0.0, #2=0.0
  'Does anyone in my family have food restrictions?': #1=0.0, #2=0.0, #3=0.0
  The second query shares no words with 'allergic to peanuts', so it scores 0.0.
  A good embedding model should score memory #2 highest: it compares meaning, not just words.
```

Memory #1 ("lives in Manchester") was added by the app from a signup form, not by the model. Session 2 starts with an empty conversation: everything it knows about Mia arrives through `recall` results.

## Test it

```bash
pytest 05-vector-memory
```

## Things to try

- Lower `min_score` in `VectorMemory.search` to `0.0`. What starts showing up in `recall` results?
- Remember "prefers aisle seats" in a third session. Now both seat facts match. How would you mark the old one as replaced? (Hint: [5.5](../../docs/05-memory/05.5-memory-design-trade-offs.md).)
- With an OpenAI key, run with `OpenAIEmbedder()` and compare the scores for the "food restrictions" query.
