# 17 · Support agent triage

A customer support agent that handles three conversations: one it answers, one it must hand to a person because of the refund policy, and one where the customer asks for a human. Hard rules, the refund limit and the step limit are enforced in code. Used in [17.2 Customer support agent](../../docs/17-case-studies/17.2-customer-support-agent.md).

What to notice:

- **Hard rules first.** "Let me speak to a real person" never reaches the model.
- **Routing.** One cheap model call returns JSON with an intent and a confidence. Invalid JSON or low confidence falls back to the safest tool set.
- **Least privilege.** An order-status conversation does not even see the `issue_refund` tool.
- **Policy in code.** The model asked for a 189 EUR refund; `issue_refund` refused it, and the model handed off with a summary instead.
- **Warm handoff.** Every ticket carries a summary, so the human doesn't have to ask the customer again.

## Run it

```bash
cd examples
python 17-support-agent-triage/main.py
```

Output (offline, with `MockLLM`):

```text
Customer: Where is my monitor arm? Order A-300.
  router: intent=order_status confidence=0.95
  tool: lookup_order({"order_id": "A-300"}) -> ok
  agent: answered
  -> resolved by agent: Your monitor arm (order A-300) has shipped and should arrive on 15 November.

Customer: The chair from order A-200 arrived broken. I want my money back.
  router: intent=refund confidence=0.9
  tool: lookup_order({"order_id": "A-200"}) -> ok
  tool: issue_refund({"order_id": "A-200", "amount_eur": 189, "reason": "Arriv...) -> refused
  tool: handoff_to_human({"reason": "Refund above auto limit", "summary": "Order A...) -> ok
  -> resolved by human: I've passed this to a colleague (ticket T-001). They can see everything we discussed.

Customer: This is useless. Let me speak to a real person.
  hard rule: asked for a human -> ticket T-002
  -> resolved by human: I'm passing you to a colleague now (ticket T-002).

Human queue:
  T-001 [Refund above auto limit] Order A-200, office chair, 189 EUR, delivered 2026-11-10, arrived broken. Customer wants a full refund. Order checked; refund refused by policy (limit 50 EUR).
  T-002 [asked for a human] Customer wrote: This is useless. Let me speak to a real person.
```

## Test it

```bash
pytest 17-support-agent-triage
```

## Things to try

- Add a `cancel_order` tool that works only for orders that have not shipped, and check that rule in code.
- Write five tricky customer messages ("I'm not angry, but my lawyer friend says...") and see which ones the regex rules get wrong. What would you use instead?
- Add a rule that hands off after the customer has written three messages without a resolution.
