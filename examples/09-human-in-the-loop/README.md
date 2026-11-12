# 09 · Human-in-the-loop

A support agent may look up orders freely, but a refund over $20 needs a person, who can approve, edit or reject it. The run can pause, save its state as JSON, and resume later with the decision. The model can also escalate the whole case. Used in [9.6 Human-in-the-loop](../../docs/09-agent-design-patterns/09.6-human-in-the-loop.md).

## Run it

```bash
cd examples
python 09-human-in-the-loop/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Order 1234: the customer says the blender arrived broken and wants their money back.

PART 1: pause, save state, a human edits the refund, resume
  status: paused; waiting on issue_refund({'order_id': '1234', 'amount': 99.0, 'reason': 'arrived broken'})
  saved state: 762 bytes of JSON
  tool: get_order({'order_id': '1234'}) -> {"order_id": "1234", "item": "Blender", "price": 89.0, "shipping": 0.0, "status": "delivered"}
  paused: issue_refund({'order_id': '1234', 'amount': 99.0, 'reason': 'arrived broken'}) needs approval (refund over $20)
  human: edit -> {'order_id': '1234', 'amount': 89.0, 'reason': 'arrived broken'} (Shipping was free, so refund the item price only.)
  tool: issue_refund({'order_id': '1234', 'amount': 89.0, 'reason': 'arrived broken'}) -> Refunded $89.00 for order 1234 (ref R-7781).
  status: done
  answer: I've refunded $89.00 for the broken blender on order 1234 (ref R-7781). The customer should see it in 3-5 working days.

PART 2: an approval callback rejects the refund, the agent escalates
  tool: get_order({'order_id': '1234'}) -> {"order_id": "1234", "item": "Blender", "price": 89.0, "shipping": 0.0, "status": "delivered"}
  human: reject (Ask the customer for photos of the damage first.)
  tool: issue_refund NOT run (rejected)
  escalated: Refund for broken blender (order 1234) was rejected pending photos. Please contact the customer.
  status: escalated

Refunds actually issued: [{'order_id': '1234', 'amount': 89.0, 'reason': 'arrived broken'}]
```

Part 1 shows pause and resume: the run stops at the refund, the state is saved as JSON, and a *new* agent object resumes it with the human's edited amount. Part 2 shows an approval callback that rejects the refund; the model reads the rejection as an error result and escalates. `REFUNDS` at the end shows that only the approved refund ran.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 09-human-in-the-loop
```

## Things to try

- Change `AUTO_APPROVE_LIMIT` to 100. What happens in part 1?
- Write an approver that asks on the command line with `input()` and returns a `Decision`.
- Save the paused state to a file, stop the program, and resume from the file in a second run.
