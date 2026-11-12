# 01 · How LLMs work: statelessness and tokens

Two facts every agent depends on, shown in code. Used in [1.4 How LLMs work](../../docs/01-foundations/01.4-how-llms-work.md).

1. **The API is stateless.** The model remembers nothing between calls; you resend the conversation each time.
2. **So input grows every turn,** and you pay for every token you resend.

## Run it

```bash
cd examples
python 01-how-llms-work/main.py
```

Output (offline, with `MockLLM`; token counts are estimates):

```text
1) The API is stateless
   Without history: I'm sorry, I don't know your name. You haven't told me.
   With history:    Your name is Sam.

2) The input grows every turn, because we resend everything
   turn 1:    8 input tokens  █
   turn 2:   39 input tokens  ███████
   turn 3:   85 input tokens  █████████████████

3) Counting tokens before you send
   29 tokens, estimate (~4 characters per token)
```

With `LLM_PROVIDER=anthropic`, step 3 uses Anthropic's token counting API and prints an exact count.

## Test it

```bash
pytest 01-how-llms-work
```
