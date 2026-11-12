# 13 · PII redaction

Keep personal data and secrets out of prompts and logs. Used in [13.6 Secrets & PII handling](../../docs/13-safety-and-guardrails/13.6-secrets-and-pii.md).

| Piece | What it does |
| --- | --- |
| `Redactor.redact` | Swaps emails, phone numbers, card numbers (Luhn-checked) and API keys for placeholders such as `<EMAIL_1>`. The same value always gets the same placeholder |
| `Redactor.restore` | Puts contact details back inside the tool layer and in the reply to the user. Card numbers and keys are never restored, only masked (`card ending 4242`, `[API_KEY]`) |
| `RedactingFilter` | A `logging.Filter` that scrubs every log line, one way |
| `run_agent` | The model only ever sees placeholders; the real address is filled in when `send_email` runs |

The regexes catch well-formed data only. They miss names, addresses and anything unusual. Production systems add a trained PII detector, such as [Presidio](https://data-privacy-stack.github.io/presidio/).

## Run it

```bash
cd examples
python 13-pii-redaction/main.py
```

Output (offline, with `MockLLM`):

```text
1) What the model sees
   Hi, I'm Ada (<EMAIL_1>, <PHONE_1>). I was charged twice on card <CARD_1> for order 1234567890123. Please email me a receipt.

2) Run (the logs are scrubbed)
   log: user: Hi, I'm Ada ([EMAIL], [PHONE]). I was charged twice on card [CARD] for order 1234567890123. Please email me a receipt.
   log: tool send_email({'to': '[EMAIL]', 'body': 'Hi Ada, we found the double charge on card ending 4242 and will refund it.'})

3) What the user sees
   I've emailed ada@example.com to confirm the refund of the double charge on card ending 4242.

4) What the email tool received
   to=ada@example.com
   body='Hi Ada, we found the double charge on card ending 4242 and will refund it.'

5) Secrets: my key is <API_KEY_1>
```

Notice that the 13-digit order number is left alone: it fails the Luhn check, so it is not a card number. Notice too that the name "Ada" gets through. Regexes can't find names.

## Test it

```bash
pytest 13-pii-redaction
```

## Things to try

- Add a pattern for your country's national ID or tax number, with a test for a near-miss that must *not* match.
- Write the `mapping` to a store with a short expiry instead of keeping it in memory. What happens if a run resumes after it expires?
- Add `RedactingFilter` to the root logger so third-party libraries' logs are scrubbed too.
