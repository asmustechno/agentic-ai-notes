# 01 · Chatbot vs workflow vs agent

One customer question, answered three ways. Used in [1.2 Chatbot vs workflow vs agent](../../docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md) and [1.1 What is an AI agent?](../../docs/01-foundations/01.1-what-is-an-ai-agent.md).

> *"Where is my order 1234? Will it arrive before Friday?"*

| Approach | Who decides the steps? | Model calls | Tools |
| --- | --- | --- | --- |
| `chatbot()` | Nobody: one reply | 1 | none |
| `workflow()` | Your code | 1 | called by code |
| `agent()` | The model | 3 | called when the model asks |

## Run it

```bash
cd examples
python 01-chatbot-workflow-agent/main.py
```

Output (offline, with `MockLLM`):

```text
Customer: Where is my order 1234? Will it arrive before Friday?

1) CHATBOT  (one call, no tools)
   I'm sorry, I can't look up orders. Please check your confirmation email for tracking details.

2) WORKFLOW (code decides the steps)
   Good news! Your desk lamp (order 1234) has shipped with FastShip and is due on Thursday, so it should arrive before Friday.

3) AGENT    (the model decides the steps)
   tool: get_order({'order_id': '1234'}) -> {"item": "Desk lamp", "status": "shipped", "carrier": "FastShip", "tracking_id": "FS-998"}
   tool: get_tracking({'tracking_id': 'FS-998'}) -> {"location": "Regional depot", "estimated_delivery": "Thursday"}
   Your desk lamp (order 1234) is at the FastShip regional depot and is due on Thursday, so it should arrive before Friday.
```

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to see a real model make the same decisions.

## Test it

```bash
pytest 01-chatbot-workflow-agent
```

## Things to try

- Ask the workflow `"Where is my order?"` (no number). Then think about how the agent could handle it.
- Add a `cancel_order` tool. Which of the three approaches needs the least code change?
