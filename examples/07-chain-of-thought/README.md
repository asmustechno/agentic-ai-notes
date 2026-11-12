# 07 · Chain-of-thought by prompting

Asks one word problem two ways: "answer with just the number", and "think step by step inside `<thinking>` tags, then put the result in `<answer>` tags". Your code keeps the reasoning for logs and shows the user only the answer. Used in [7.1 Chain-of-thought & extended thinking](../../docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md).

The problem comes from Figure 1 of [Wei et al. (2022)](https://arxiv.org/abs/2201.11903). The offline replies are **scripted** to mirror that figure, where standard prompting gave 27 and chain-of-thought gave 9. They are not output from a current model: current models usually get this one right either way, because they reason internally before answering.

## Run it

```bash
cd examples
python 07-chain-of-thought/main.py
```

Output (offline, with `MockLLM`):

```text
Q: The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, how many apples do they have?

1) Direct            answer: 27   (output tokens: 1)
2) Chain-of-thought  answer: 9    (output tokens: 35)
   reasoning kept for logs: The cafeteria started with 23 apples. They used 20, so 23 - 20 = 3. They bought 6 more, so 3 + 6 = 9.
```

With a real model, try different effort levels (the wrapper passes `ANTHROPIC_EFFORT` to Claude as `output_config={"effort": ...}`):

```bash
LLM_PROVIDER=anthropic ANTHROPIC_EFFORT=low python 07-chain-of-thought/main.py
```

## Test it

```bash
pytest 07-chain-of-thought
```

## Things to try

- Write a harder problem (several steps, a trap) and compare the two prompts with a real model at `low` effort.
- Make `extract` stricter: return `None` when the `<answer>` tag is missing, and decide what your app should do then.
