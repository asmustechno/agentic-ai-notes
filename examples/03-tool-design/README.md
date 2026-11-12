# 03 · Designing a good tool

A bad tool and a good tool for the same job, side by side. The good one, `search_orders`, has a clear name and a description that says *when* to call it, inputs validated by [pydantic](https://docs.pydantic.dev/latest/) (which also generates the JSON Schema), error messages that say how to fix the call, concise output with an opt-in detailed format, and pagination. Used in [3.4 Designing good tools](../../docs/03-tools-and-function-calling/03.4-designing-good-tools.md) and [3.2 JSON Schema for tool definitions](../../docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md).

## Run it

```bash
cd examples
python 03-tool-design/main.py
```

Output (offline, with `MockLLM`; the generated schema is shortened here):

```text
1) What the model sees for each tool

BAD : {"name": "get_data", "description": "Gets data.", "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}}}

GOOD: {
  "name": "search_orders",
  "description": "Search one customer's orders by email address, newest first. Call this whenever the user asks about an order's status, delivery date or history. Returns one line per order and says when there are more pages. Do not guess order details: call this tool.",
  "input_schema": {
    "additionalProperties": false,
    "properties": {
      "customer_email": {"description": "The customer's email address, e.g. 'sam@example.com'.", "type": "string"},
      "status": {
        "anyOf": [
          {"enum": ["pending", "shipped", "delivered", "cancelled"], "type": "string"},
          {"type": "null"}
        ],
        "default": null,
        "description": "Only return orders with this status. Omit to return every status."
      },
      ...
    },
    "required": ["customer_email"],
    "type": "object"
  }
}

2) Same question, output size

BAD  get_data returns  2926 characters (about 731 tokens): every field of all 12 orders
GOOD search_orders returns 270 characters (about 67 tokens):
#1041 Blue kettle: shipped, ETA 2026-11-15
#1022 Tea towels (3): delivered, ETA 2026-10-30
#1010 Mug #10: delivered, ETA 2026-09-01
#1009 Mug #9: delivered, ETA 2026-09-01
#1008 Mug #8: delivered, ETA 2026-09-01
Showing 1-5 of 12 orders. Call again with page=2 for more.

3) An agent run: a bad call, a helpful error, a fixed call

call 1: search_orders({'customer_email': 'sam@example.com', 'status': 'shiped', 'page_size': 50})
ERROR Invalid arguments for search_orders:
- status: Input should be 'pending', 'shipped', 'delivered' or 'cancelled' (you sent 'shiped')
- page_size: Input should be less than or equal to 20 (you sent 50)
Example of a valid call: {"customer_email": "sam@example.com", "status": "shipped"}

call 2: search_orders({'customer_email': 'sam@example.com', 'status': 'shipped'})
#1041 Blue kettle: shipped, ETA 2026-11-15
Showing 1-1 of 1 order.

Answer: Yes. Sam's blue kettle (order #1041) has shipped and is due on 15 November 2026.
```

The token figures use the rough "4 characters per token" rule from [1.4](../../docs/01-foundations/01.4-how-llms-work.md).

## Test it

```bash
pytest 03-tool-design
```

## Things to try

- Add an `order_no` filter to `SearchOrdersInput`. What appears in the schema, and what error does `{"order_no": "abc"}` give?
- Make `search_orders` return `json.dumps(page)` instead of one line per order. Compare the sizes.
- Rewrite the bad tool's description so a model could use it. How much of the good tool's design do you end up copying?
