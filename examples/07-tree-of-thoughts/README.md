# 07 · Tree of thoughts on the Game of 24

A breadth-first tree-of-thoughts search on the Game of 24 (make 24 from four numbers), the main task in [Yao et al. (2023)](https://arxiv.org/abs/2305.10601). Each round the model **proposes** next steps, our code **checks** the arithmetic, the model **evaluates** each new state as sure / likely / impossible, and we **keep** the best few. Used in [7.4 Tree-of-thoughts (overview)](../../docs/07-planning-and-reasoning/07.4-tree-of-thoughts.md).

Offline, two small Python functions stand in for the model: one lists possible steps, the other uses a quick look-ahead plus "too big / too small" rules of thumb. The evaluator is not a perfect solver (it ignores division), so the search still matters.

## Run it

```bash
cd examples
python 07-tree-of-thoughts/main.py
```

Output (offline, with `MockLLM`):

```text
Input: 4 9 10 13

depth 1: 18 proposals, kept [6 9 13], [3 4 9], [4 4 10]
depth 2: 31 proposals, kept [4 6]
depth 3: 3 proposals, kept [24]

Model calls: 49 (one chain-of-thought attempt would be 1)

Solution:
  10 - 4 = 6 (left: 6 9 13)
  13 - 9 = 4 (left: 4 6)
  4 * 6 = 24 (left: 24)
```

What to notice: about 50 model calls to solve one puzzle. Tree of thoughts buys accuracy with many more calls; use it only where that trade is worth it.

## Test it

```bash
pytest 07-tree-of-thoughts
```

## Things to try

- Set `breadth=1` (greedy search). Does it still find a solution? How many calls does it make?
- Try `[1, 2, 3, 4]` and `[3, 3, 8, 8]`. The second needs fractions (8 / (3 - 8 / 3)); why can't this version solve it?
