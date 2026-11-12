# 12 · LLM-as-judge

A rubric-based judge that returns a structured verdict per criterion, a pairwise judge that asks twice with the answers swapped to catch position bias, and a calibration step that measures agreement and Cohen's kappa against human labels. Used in [12.3 LLM-as-judge](../../docs/12-evaluation/12.3-llm-as-judge.md).

Offline, the judge model is a `MockLLM` driven by a crude keyword function (`keyword_judge`), so the run is repeatable. Set `LLM_PROVIDER=anthropic` or `openai` and the same prompts go to a real model; the same parser reads its verdicts.

## Run it

```bash
cd examples
python 12-llm-judge/main.py
```

Output (offline, with `MockLLM`):

```text
Pointwise rubric grading
  c1: judge=pass  human=pass  correct=True  grounded=True  concise=True
  c2: judge=fail  human=fail  correct=False grounded=True  concise=True
  c3: judge=fail  human=pass  correct=False grounded=True  concise=True    <-- disagrees with human
  c4: judge=fail  human=fail  correct=True  grounded=False concise=True
  c5: judge=fail  human=fail  correct=True  grounded=True  concise=False
  c6: judge=fail  human=fail  correct=False grounded=True  concise=True

Agreement with human labels: 83%
Cohen's kappa:               0.57
Review c3: missing facts: ['5 business days']; unsupported numbers: none

Pairwise comparison of c1 (A) vs c2 (B), asked in both orders
  fair judge:            A
  position-biased judge: inconsistent
```

Things to notice:

- Each criterion is graded separately, so you can see *why* c4 failed (it invented a $10 voucher) and c5 failed (too long).
- Calibration found the judge's blind spot: c3 says "5 working days", which a person accepts and the keyword judge does not. Disagreements are the cases to read.
- The position-biased judge picks "first" both times, so the two orders disagree and the comparison is thrown out instead of counted.

## Test it

```bash
pytest 12-llm-judge
```

## Things to try

- Make the judge accept paraphrases: in `keyword_judge`, also accept "working days". Does agreement reach 100%?
- Write a `verbosity_biased_judge` that always prefers the longer answer. Does the swap check catch it? (Think about why not.)
- Run with a real model and compare its verdicts with the human labels in `CASES`.
