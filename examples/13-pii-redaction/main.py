"""Keep secrets and personal data out of prompts and logs.

Three tools in one file:

    Redactor            swaps emails, phone numbers, card numbers and API keys for
                        placeholders like <EMAIL_1>, and can put them back later
    RedactingFilter     a logging.Filter that scrubs every log line, one way
    run_agent           the model sees only placeholders; real values are restored
                        at the last moment, inside the tool that needs them

Regexes catch well-formed data only. Real systems add a trained PII detector
(for example Presidio) for names and addresses, which regexes miss.

    python main.py                         # from this folder
    python 13-pii-redaction/main.py        # from examples/

Read alongside docs/13-safety-and-guardrails/13.6-secrets-and-pii.md.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402


def luhn_ok(number: str) -> bool:
    """The checksum every real card number passes. Cuts false positives on long numbers."""
    digits = [int(d) for d in re.sub(r"\D", "", number)][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
    return len(digits) >= 13 and total % 10 == 0


# Order matters: secrets first, so a key is not half-matched as a phone number.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("API_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),  # OpenAI- and Anthropic-style keys (sk-..., sk-ant-...)
    ("API_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),  # AWS access key id
    ("API_KEY", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),  # GitHub tokens
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+\d{1,3}|0)[\d ()-]{7,}\d\b")),  # starts with +country code or 0
]


RESTORABLE = frozenset({"EMAIL", "PHONE"})


def mask(kind: str, value: str) -> str:
    """A safe, human-readable stand-in for a value that must not be shown in full."""
    if kind == "CARD":
        digits = re.sub(r"\D", "", value)
        return f"card ending {digits[-4:]}"
    return f"[{kind}]"


@dataclass
class Redactor:
    """Reversible redaction: the same value always gets the same placeholder."""

    mapping: dict[str, str] = field(default_factory=dict)  # placeholder -> real value
    _counts: dict[str, int] = field(default_factory=dict)

    def _placeholder(self, kind: str, value: str) -> str:
        for ph, real in self.mapping.items():
            if real == value:
                return ph
        self._counts[kind] = self._counts.get(kind, 0) + 1
        ph = f"<{kind}_{self._counts[kind]}>"
        self.mapping[ph] = value
        return ph

    def redact(self, text: str) -> str:
        for kind, rx in PATTERNS:
            def swap(m: re.Match[str], kind: str = kind) -> str:
                if kind == "CARD" and not luhn_ok(m.group()):
                    return m.group()  # a long number that is not a card (an order id, say)
                return self._placeholder(kind, m.group())

            text = rx.sub(swap, text)
        return text

    def restore(self, text: str, kinds: frozenset[str] = RESTORABLE) -> str:
        """Put real values back for `kinds`; mask the rest (card numbers and keys never come back)."""
        for ph, real in self.mapping.items():
            kind = ph[1:].rsplit("_", 1)[0]
            text = text.replace(ph, real if kind in kinds else mask(kind, real))
        return text


class RedactingFilter(logging.Filter):
    """Scrub every record before any handler writes it. One way: logs never hold the mapping."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for kind, rx in PATTERNS:
            msg = rx.sub(lambda m, k=kind: m.group() if k == "CARD" and not luhn_ok(m.group()) else f"[{k}]", msg)
        record.msg, record.args = msg, None
        return True


def get_logger() -> logging.Logger:
    log = logging.getLogger("agent")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("   log: %(message)s"))
        handler.addFilter(RedactingFilter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


# --------------------------------------------------------------------------- an agent that only sees placeholders

SENT: list[dict[str, str]] = []


def send_email(to: str, body: str) -> str:
    SENT.append({"to": to, "body": body})
    return f"Sent to {to}."


EMAIL_SPEC: ToolSpec = {
    "name": "send_email",
    "description": "Send an email. Placeholders like <EMAIL_1> are filled in for you.",
    "input_schema": {
        "type": "object",
        "properties": {"to": {"type": "string"}, "body": {"type": "string"}},
        "required": ["to", "body"],
    },
}
SYSTEM = (
    "You are a support assistant. Personal data has been replaced by placeholders such as "
    "<EMAIL_1>. Use the placeholders as they are; never ask for the real values."
)
MESSAGE = (
    "Hi, I'm Ada (ada@example.com, +44 7700 900123). I was charged twice on card "
    "4242 4242 4242 4242 for order 1234567890123. Please email me a receipt."
)
SCRIPT = [
    MockLLM.tool_call(
        "send_email",
        {"to": "<EMAIL_1>", "body": "Hi Ada, we found the double charge on <CARD_1> and will refund it."},
    ),
    "I've emailed <EMAIL_1> to confirm the refund of the double charge on <CARD_1>.",
]


def run_agent(llm: LLM, message: str, redactor: Redactor, log: logging.Logger) -> str:
    safe = redactor.redact(message)  # ① redact before the model sees anything
    log.info("user: %s", message)  # ② the logger scrubs this line too
    messages: list[Message] = [user(safe)]
    for _ in range(4):
        reply = llm.chat(messages, system=SYSTEM, tools=[EMAIL_SPEC])
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return redactor.restore(reply.text)  # ④ restore contact details for the user; cards stay masked
        for call in reply.tool_calls:
            real_args = {k: redactor.restore(v) for k, v in call.arguments.items()}  # ③ restore inside the tool layer
            log.info("tool %s(%s)", call.name, real_args)
            messages.append(tool_result(call.id, redactor.redact(send_email(**real_args))))
    return "Step limit reached."


def main() -> None:
    redactor = Redactor()
    log = get_logger()
    print("1) What the model sees")
    print(f"   {redactor.redact(MESSAGE)}\n")
    print("2) Run (the logs are scrubbed)")
    llm = get_llm(mock_responses=SCRIPT)
    answer = run_agent(llm, MESSAGE, Redactor(), log)
    print(f"\n3) What the user sees\n   {answer}")
    print(f"\n4) What the email tool received\n   to={SENT[-1]['to']}\n   body={SENT[-1]['body']!r}")
    print(f"\n5) Secrets: {redactor.redact('my key is sk-ant-api03-' + 'x' * 24)}")


if __name__ == "__main__":
    main()
