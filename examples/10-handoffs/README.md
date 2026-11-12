# 10 · Handoffs

A triage agent reads the customer's message and hands the conversation to a billing or a tech specialist. After the handoff, the specialist is in charge: it uses its own instructions and tools and answers the user directly. Used in [10.3 Peer-to-peer & handoffs](../../docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md).

What to notice:

- Each handoff is offered to the model as a tool called `transfer_to_<agent>`, the same convention the OpenAI Agents SDK uses.
- Triage is called **once**. It never gets control back, unlike the supervisor in [`10-supervisor`](../10-supervisor/README.md).
- By default the receiving agent sees the whole conversation. `build_runner(..., filter_history=True)` gives it only the user's last message instead.
- `max_handoffs` stops two agents from bouncing a customer between them forever.

## Run it

```bash
cd examples
python 10-handoffs/main.py
```

Output (offline, with `MockLLM`):

```text
User: Hi, I was charged twice for my Pro plan this month. My customer id is C-1042.

[triage] handoff -> billing (reason: Possible duplicate charge on the Pro plan.)
[billing] list_charges({'customer_id': 'C-1042'}) -> [{"invoice_id": "INV-881", "date": "2026-11-01", "amount_...
[billing] open_refund_request({'invoice_id': 'INV-882', 'reason': 'Duplicate charge on 2026-11-01'}) -> {"refund_request": "RR-001", "invoice_id": "INV-882", "et...
[billing] answer: You're right: you were charged 20 EUR twice on 1 November (INV-881 and INV-882). I've opened refund request RR-001 for INV-882. The money should be back in 5-7 days.

Answered by: billing
Answer: You're right: you were charged 20 EUR twice on 1 November (INV-881 and INV-882). I've opened refund request RR-001 for INV-882. The money should be back in 5-7 days.
```

## Test it

```bash
pytest 10-handoffs
```

## Things to try

- Add a `transfer_to_human` handoff that writes a ticket instead of switching agent.
- Ask a mixed question ("I was charged twice and the app won't sync") with a real model. Which agent ends up answering, and does the other half get lost?
- Turn on `filter_history=True`. What does billing lose, and what does it gain?
