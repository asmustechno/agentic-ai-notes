# 08 · The evaluator–optimizer loop

A generator writes a customer email; plain-Python hard checks and a separate evaluator model with a rubric grade it; the feedback goes back to the generator until a draft passes. `optimize()` is a reusable building block. Used in [8.2 The evaluator–optimizer loop](../../docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md) and [9.5 Evaluator–optimizer](../../docs/09-agent-design-patterns/09.5-evaluator-optimizer.md).

## Run it

```bash
cd examples
python 08-evaluator-optimizer/main.py
```

Output (offline, with `MockLLM`):

```text
--- round 1: 64 words -> FAIL (score 0)
Dear customer, we are very sorry. Unfortunately, due to an unexpected and highly unusual issue at our main fulfilment warehouse, which our operations team is currently investigating as a matter of priority, your recent order has been delayed. We now expect it to arrive on Friday. We truly value your business and apologise for any inconvenience this may have caused you and your family.
feedback: Too long: 64 words, the limit is 50.
Must mention the order number A-1042.

--- round 2: 29 words -> FAIL (score 60)
Hi there, I'm sorry: your order A-1042 is running 3 days late because of a problem at our warehouse. It should now arrive on Friday. We appreciate your patience.
feedback: Criterion 3 unmet: offer the code SORRY10 and say it gives 10% off.

--- round 3: 40 words -> PASS (score 95)
Hi there, I'm sorry: your order A-1042 is running 3 days late because of a problem at our warehouse. It should now arrive on Friday. As a thank-you for your patience, use code SORRY10 for 10% off your next order.
feedback: All criteria met.

Result: passed after 3 round(s).
Model calls: generator 3, evaluator 2
```

Round 1 fails the code checks (too long, no order number), so the evaluator model is not even called. Round 2 fails the rubric. Round 3 passes. If nothing passes, `optimize()` returns the best-scoring draft with `passed=False`.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 08-evaluator-optimizer
```

## Things to try

- Lower `MAX_WORDS` to 30. Which round fails now, and why?
- Make the evaluator reply with invalid JSON. What does `parse_verdict` do, and why is that the safe choice?
- Reuse `optimize()` for another task: write a `generate` and an `evaluate` for a post under 280 characters.
