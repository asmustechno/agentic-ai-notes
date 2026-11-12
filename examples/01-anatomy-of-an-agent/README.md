# 01 · Anatomy of an agent

A small agent with its five parts labelled in the code: ① model, ② instructions, ③ tools, ④ memory, ⑤ loop. Used in [1.5 Anatomy of an agent](../../docs/01-foundations/01.5-anatomy-of-an-agent.md).

## Run it

```bash
cd examples
python 01-anatomy-of-an-agent/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Is it warmer in Paris or Rome right now, and by how much?

step 1: get_weather({'city': 'Paris'}) -> {"city": "Paris", "temp_c": 14}
step 1: get_weather({'city': 'Rome'}) -> {"city": "Rome", "temp_c": 19}
step 2: calculator({'expression': '19 - 14'}) -> 5
step 3: answer

Answer: Rome is warmer: 19°C versus 14°C in Paris, a difference of 5°C.
```

Notice that step 1 runs **two** tools: the model asked for both cities at once.

## Test it

```bash
pytest 01-anatomy-of-an-agent
```

## Things to try

- Remove the `facts` line in `build_agent`. What changes in the system prompt the model receives?
- Set `max_steps=1`. What does the agent answer, and why?
- Add a `convert_to_fahrenheit` tool and describe it to the model.
