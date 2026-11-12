# 03 · The function-calling round trip

One question, one tool, four steps, printed as the exact JSON each provider sends and receives: the Anthropic Messages API and the OpenAI Chat Completions API. The payloads are built by the same converters the shared wrapper uses (`to_anthropic_messages`, `to_openai_messages`, `to_openai_tools`). Used in [3.3 How function calling works](../../docs/03-tools-and-function-calling/03.3-how-function-calling-works.md).

## Run it

```bash
cd examples
python 03-function-calling-roundtrip/main.py
```

Output (offline; shortened here, run it to see every payload in full):

```text
======================================================================
STEP 1  Your code sends the question and the tool definitions

--- Anthropic request body
{
  "model": "claude-opus-5-5",
  "max_tokens": 1024,
  "system": "You are a helpful assistant. Use tools for live data.",
  "tools": [
    {
      "name": "get_weather",
      "description": "Get the current weather for one city. Call this whenever the user asks about weather.",
      "input_schema": {
        "type": "object",
        "properties": {
          "city": {"type": "string", "description": "City name, e.g. 'Paris'."},
          ...
        },
        "required": ["city"]
      }
    }
  ],
  "messages": [{"role": "user", "content": "What's the weather in Paris?"}]
}

--- OpenAI request body
{
  "model": "YOUR_OPENAI_MODEL",
  "max_completion_tokens": 1024,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather for one city. Call this whenever the user asks about weather.",
        "parameters": { ...the same JSON Schema... }
      }
    }
  ],
  "messages": [
    {"role": "system", "content": "You are a helpful assistant. Use tools for live data."},
    {"role": "user", "content": "What's the weather in Paris?"}
  ]
}

======================================================================
STEP 2  The model replies with a tool call instead of an answer
...
Both parse to the same neutral shape:
  anthropic -> ToolCall(id='toolu_01A09q90qw90lq', name='get_weather', arguments={'city': 'Paris'}, error=None)  stop_reason=tool_use
  openai    -> ToolCall(id='call_abc123', name='get_weather', arguments={'city': 'Paris'}, error=None)  stop_reason=tool_use

======================================================================
STEP 3  Your code runs the tool and sends the result back

--- Anthropic: the last two messages of the next request
[
  {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "I'll check the current weather in Paris."},
      {
        "type": "tool_use",
        "id": "toolu_01A09q90qw90lq",
        "name": "get_weather",
        "input": {"city": "Paris"}
      }
    ]
  },
  {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01A09q90qw90lq",
        "content": "{\"city\": \"Paris\", \"temp\": 18, \"unit\": \"celsius\", \"sky\": \"sunny\"}"
      }
    ]
  }
]

--- OpenAI: the last two messages of the next request
[
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "{\"city\": \"Paris\", \"temp\": 18, \"unit\": \"celsius\", \"sky\": \"sunny\"}"
  }
]

======================================================================
STEP 4  The model reads the result and answers

Answer: It's 18°C and sunny in Paris right now.
```

The step 2 responses are samples in each provider's real shape; the IDs and token counts in them are illustrative. Step 4 goes through `get_llm()`, so with `LLM_PROVIDER=anthropic` or `openai` it makes the real two calls.

## Test it

```bash
pytest 03-function-calling-roundtrip
```

## Things to try

- Add a second tool, `get_forecast(city, days)`, and look at how both request bodies change.
- Mark the tool result as an error with `tool_result(id, "City not found", is_error=True)`. What changes in each payload? (Hint: OpenAI has no `is_error` field.)
