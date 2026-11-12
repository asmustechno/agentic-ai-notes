# 09 · Routing

A small model classifies support tickets into a category and a difficulty. Code validates the label, then sends the ticket to a specialised prompt on a small or a large model. Used in [9.2 Routing](../../docs/09-agent-design-patterns/09.2-routing.md).

## Run it

```bash
cd examples
python 09-routing/main.py
```

Output (offline, with `MockLLM`):

```text
Ticket: I was charged twice for my March subscription. Can you fix it?
  route -> billing / easy -> small model
  reply -> Sorry about the double charge. I've passed this to a billing specialist, who will check your March payments and confirm the refund of any duplicate.

Ticket: Since updating to 2.3, the Android app crashes every time I sync my bank. I've reinstalled twice.
  route -> technical / hard -> large model
  reply -> Thanks for the details. 1) Tell me your Android version. 2) Open Settings > Sync and note the bank name. 3) Turn off battery optimisation for the app and try once more.

Ticket: Do you offer a student discount?
  route -> general / easy -> small model   [invalid label {"category": "sales", "difficulty": "easy"}, used fallback]
  reply -> I can't confirm discounts from here. You can see every current plan under Settings > Plans, and our sales team can tell you about any student offers.
```

The third ticket gets the label `sales`, which is not a known category, so it falls back to a safe default and the fallback is flagged. With `LLM_PROVIDER=anthropic`, the classifier and easy tickets use `claude-haiku-5-5` (override with `ANTHROPIC_SMALL_MODEL`) and hard tickets use your default model; with OpenAI, set `OPENAI_SMALL_MODEL`.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 09-routing
```

## Things to try

- Add a `refund` category with its own prompt. What else has to change?
- Make the classifier reply with prose. Which route does the ticket take?
- If 70% of tickets are easy, roughly how much of the large model's cost does routing save?
