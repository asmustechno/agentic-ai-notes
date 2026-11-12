# 13 · Approval gate

A billing agent whose tools have risk tiers. Reads run at once, writes run and are logged, and irreversible actions (refunds) stop for a human, who sees a dry-run preview of exactly what will happen. Every decision is written to an append-only JSON Lines audit log. Used in [13.5 Human approval for risky actions](../../docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md).

| Tier | Tools | What the gate does |
| --- | --- | --- |
| `read` | `get_invoice` | Runs immediately |
| `write` | `add_note` | Runs, logged |
| `irreversible` | `refund` | Dry run → preview → human decision → runs exactly the approved arguments |

## Run it

```bash
cd examples
python 13-approval-gate/main.py
```

Output (offline, with `MockLLM` and a scripted approver that approves the first refund and denies the second):

```text
Goal: Ada wants full refunds for INV-1001 and INV-1002. Please sort it out.

  [approval 986d40f0e6e2] Would refund £40.00 to Ada's card ending 4242 for INV-1001. -> APPROVED by sam@billing
  [approval f646186caaf1] Would refund £950.00 to Ada's card ending 4242 for INV-1002. -> DENIED by sam@billing

Answer: I refunded £40.00 for INV-1001. The £950.00 refund for INV-1002 was denied by a reviewer, so I added a note and it has been escalated.

Audit log:
  executed  get_invoice {"invoice_id": "INV-1001"}  risk=read
  executed  get_invoice {"invoice_id": "INV-1002"}  risk=read
  approved  refund      {"invoice_id": "INV-1001", "amount_gbp": 40.0}  by sam@billing
  executed  refund      {"invoice_id": "INV-1001", "amount_gbp": 40.0}  risk=irreversible
  denied    refund      {"invoice_id": "INV-1002", "amount_gbp": 950.0}  by sam@billing
  executed  add_note    {"invoice_id": "INV-1002", "text": "Full refund denied by reviewer; escalated."}  risk=write

Refunds actually made: [{'invoice_id': 'INV-1001', 'amount_gbp': 40.0}]
```

The denial goes back to the model as an error tool result, so it can adapt (here it adds a note instead of retrying). The fingerprint (`986d40f0e6e2`) is a hash of the tool name and arguments: the approval covers those exact arguments and nothing else.

To approve in the terminal yourself, pass `cli_approver` instead of `scripted_approver(...)` in `main()`. It denies anything other than `y`.

## Test it

```bash
pytest 13-approval-gate
```

## Things to try

- Auto-approve refunds under £10 but still log them. Which tier should that rule live in?
- Add an approval timeout: if no one answers within N minutes, deny.
- Make `delete_invoice` a new irreversible tool with its own dry-run preview.
