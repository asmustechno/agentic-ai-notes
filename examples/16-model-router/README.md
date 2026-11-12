# 16 · Model router: rules and a cascade

Classifies six support tickets with three strategies, **always-large**, **rules** (pick the model before calling) and a **cascade** (try the small model, check its answer, escalate if the check fails), and compares cost and correctness. Used in [16.3 Model routing](../../docs/16-cost-and-performance/16.3-model-routing.md).

Offline, two `MockLLM`s play the small and large models. The small one is scripted to be right on easy tickets and unsure on legal-sounding ones, so the numbers show the mechanics, not real model quality. With `LLM_PROVIDER=anthropic` the tiers are `claude-haiku-5-5` and `claude-opus-5-5`; with `LLM_PROVIDER=openai`, set `OPENAI_SMALL_MODEL` and `OPENAI_LARGE_MODEL`. Costs use Claude Haiku 5.5 and Opus 5.5 prices (November 2026) and estimated token counts.

## Run it

```bash
cd examples
python 16-model-router/main.py
```

Output:

```text
always_large:
  ok  large         shipping  Where is my parcel? Tracking says it left th...
  ok  large         account   I forgot my password and the reset email nev...
  ok  large         shipping  The delivery date on my order page changed t...
  ok  large         billing   You charged my card twice for order 5521....
  ok  large         legal     Your terms say refunds within 30 days, but I...
  ok  large         legal     I was billed for a plan I cancelled in March...
  calls {'small': 0, 'large': 6}, correct 6/6, $0.4427 per 1,000 tickets

by_rules:
  ok  small         shipping  Where is my parcel? Tracking says it left th...
  ok  small         account   I forgot my password and the reset email nev...
  ok  small         shipping  The delivery date on my order page changed t...
  ok  small         billing   You charged my card twice for order 5521....
  ok  large         legal     Your terms say refunds within 30 days, but I...
  BAD small         billing   I was billed for a plan I cancelled in March...
  calls {'small': 5, 'large': 1}, correct 5/6, $0.0969 per 1,000 tickets

cascade:
  ok  small         shipping  Where is my parcel? Tracking says it left th...
  ok  small         account   I forgot my password and the reset email nev...
  ok  small         shipping  The delivery date on my order page changed t...
  ok  small         billing   You charged my card twice for order 5521....
  ok  small->large  legal     Your terms say refunds within 30 days, but I...
  ok  small->large  legal     I was billed for a plan I cancelled in March...
  calls {'small': 6, 'large': 2}, correct 6/6, $0.1777 per 1,000 tickets

always_large  6/6 correct, 100% of the always-large cost
by_rules      5/6 correct, 22% of the always-large cost
cascade       6/6 correct, 40% of the always-large cost
```

The rules miss the "agreement" ticket; the cascade's confidence check catches it, at the price of two calls for each escalated ticket. Before shipping either, measure the baseline the page recommends: the large model alone at a lower `effort`.

## Test it

```bash
pytest 16-model-router
```

The 6 tests check the routing rules, answer validation, that confident small answers are kept, escalation on low confidence or invalid output (with both attempts paid for), the three strategies on the demo tickets, and the prompt sent to the models.

## Things to try

- Lower `min_confidence` to `0.4`. What happens to cost and accuracy?
- Add a ticket that the small model gets wrong *confidently*. Which strategy catches it?
