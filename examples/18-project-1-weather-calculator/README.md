# 18 · Project 1: Weather + calculator agent

Your first tool-using agent: two tools (`get_weather` and a safe `calculator`) and an agent loop with a step limit and error handling. The full guide, with the spec, milestones and stretch goals, is [18.1 Project 1: Weather + calculator agent](../../docs/18-projects/18.1-project-1-weather-and-calculator-agent.md).

## The spec in brief

| | |
| --- | --- |
| **Goal** | Answer weather questions with real tool calls, and do every calculation with a tool instead of in the model's head. |
| **Tools** | `get_weather(city)` (fake data for six cities; optional real data from Open-Meteo) and `calculator(expression)` (numbers, `+ - * / % **`, brackets; never `eval`) |
| **Loop** | At most 5 model calls; tool errors go back to the model with `is_error`; never crashes on a bad tool call |
| **Done when** | `pytest 18-project-1-weather-calculator` passes against your code |

## Layout

```text
18-project-1-weather-calculator/
├── starter/main.py      ← you build here: runnable skeleton with # TODO markers
├── solution/main.py     ← a complete reference solution
└── tests/test_solution.py
```

## Run it

From `examples/`:

```bash
python 18-project-1-weather-calculator/starter/main.py    # tells you what is still missing
python 18-project-1-weather-calculator/solution/main.py   # the finished agent, offline
```

Output of the solution (offline, with `MockLLM`):

```text
Question: What's the average temperature in Paris and Rome right now, in °F?
  step 1: get_weather({"city": "Paris"}) -> {"city": "Paris", "temp_c": 14, "condition": "cloudy", "wind_kph": 12, "source": "fake"}
  step 1: get_weather({"city": "Rome"}) -> {"city": "Rome", "temp_c": 19, "condition": "sunny", "wind_kph": 8, "source": "fake"}
  step 2: calculator({"expression": "(14 + 19) / 2 * 9 / 5 + 32"}) -> 61.7
  step 3: answer
Answer: It's 14°C and cloudy in Paris and 19°C and sunny in Rome. The average is 16.5°C, which is 61.7°F.

Question: What's the weather in Atlantis?
  step 1: get_weather({"city": "Atlantis"}) -> Error: Unknown city 'Atlantis'. Known cities: Paris, Rome, London, Tokyo, Cairo, New York.
  step 2: answer
Answer: Sorry, I don't have weather for Atlantis. I can check Paris, Rome, London, Tokyo, Cairo or New York.
```

With a real model, ask your own question, and optionally use real weather:

```bash
LLM_PROVIDER=anthropic python 18-project-1-weather-calculator/solution/main.py "Is it warmer in Tokyo or Cairo?"
WEATHER_SOURCE=open-meteo LLM_PROVIDER=anthropic python 18-project-1-weather-calculator/solution/main.py "Weather in Oslo?"
```

## Test it

```bash
pytest 18-project-1-weather-calculator                          # tests the solution
PROJECT_TARGET=starter pytest 18-project-1-weather-calculator   # tests your starter code
```

On Windows PowerShell, set the variable first: `$env:PROJECT_TARGET="starter"`, then run `pytest`. Remove it afterwards with `Remove-Item Env:PROJECT_TARGET`.
