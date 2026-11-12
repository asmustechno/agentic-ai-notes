"""Send easy work to a small model and hard work to a large one: rule routing and a cascade.

    python main.py                       # from this folder
    python 16-model-router/main.py       # from examples/

The task: classify support tickets into a category, as JSON. Three strategies are compared:

    always-large   every ticket goes to the large model (the baseline)
    rules          cheap rules pick the model before any call
    cascade        try the small model, check its answer, escalate to the large model if the check fails

Offline, two MockLLMs play the small and large models. The small one is right on easy tickets and unsure
on hard ones; that behaviour is scripted, so the numbers show the mechanics, not real model quality.
With LLM_PROVIDER=anthropic the tiers are claude-haiku-5-5 and claude-opus-5-5; with LLM_PROVIDER=openai set
OPENAI_SMALL_MODEL and OPENAI_LARGE_MODEL.

Read alongside docs/16-cost-and-performance/16.3-model-routing.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, user  # noqa: E402

CATEGORIES = ["shipping", "billing", "account", "legal"]
SYSTEM = (
    "Classify the support ticket. Reply with JSON only: "
    '{"category": one of ' + json.dumps(CATEGORIES) + ', "confidence": a number from 0 to 1}.'
)
PRICES = {"small": (0.10, 0.50), "large": (4.00, 20.00)}  # $/MTok in/out: Claude Haiku 5.5, Claude Opus 5.5 (Nov 2026)

TICKETS: list[tuple[str, str]] = [  # (ticket, correct category)
    ("Where is my parcel? Tracking says it left the depot yesterday.", "shipping"),
    ("I forgot my password and the reset email never arrives.", "account"),
    ("The delivery date on my order page changed to next week.", "shipping"),
    ("You charged my card twice for order 5521.", "billing"),
    ("Your terms say refunds within 30 days, but I was refused on day 12. Under consumer law this is unlawful "
     "and I will file a chargeback and contact a lawyer unless this is resolved.", "legal"),
    ("I was billed for a plan I cancelled in March. My agreement says I can leave at any time, so this charge "
     "should not stand.", "legal"),
]

# --------------------------------------------------------------------------- the models


def _ticket(messages: list[Message]) -> str:
    return messages[-1]["content"].lower()


def fake_small(messages: list[Message]) -> str:
    """A scripted small model: right and confident on easy tickets, unsure on long or legal-sounding ones."""
    t = _ticket(messages)
    if any(w in t for w in ("law", "lawyer", "contract", "clause", "agreement")):
        return json.dumps({"category": "billing", "confidence": 0.45})  # plausible but wrong, and unsure
    if "track" in t or "deliver" in t or "parcel" in t:
        return json.dumps({"category": "shipping", "confidence": 0.93})
    if "password" in t:
        return json.dumps({"category": "account", "confidence": 0.91})
    return json.dumps({"category": "billing", "confidence": 0.88})


def fake_large(messages: list[Message]) -> str:
    """A scripted large model: right on every ticket in this demo."""
    t = _ticket(messages)
    for words, cat in ((("law", "lawyer", "contract", "clause", "agreement"), "legal"), (("track", "deliver", "parcel"), "shipping"),
                       (("password",), "account")):
        if any(w in t for w in words):
            return json.dumps({"category": cat, "confidence": 0.96})
    return json.dumps({"category": "billing", "confidence": 0.95})


def make_models() -> dict[str, LLM]:
    """The two tiers. Offline they are MockLLMs; with a real provider, two real models."""
    provider = (os.getenv("LLM_PROVIDER") or "mock").lower()
    if provider == "anthropic":
        from common import AnthropicLLM

        return {"small": AnthropicLLM("claude-haiku-5-5"), "large": AnthropicLLM("claude-opus-5-5")}
    if provider == "openai":
        from common import OpenAILLM

        return {"small": OpenAILLM(os.environ["OPENAI_SMALL_MODEL"]), "large": OpenAILLM(os.environ["OPENAI_LARGE_MODEL"])}
    return {
        "small": MockLLM([fake_small] * 100),
        "large": MockLLM([fake_large] * 100),
    }


# --------------------------------------------------------------------------- routing strategies

HARD_WORDS = re.compile(r"\b(law|lawyer|legal|contract|clause|chargeback|gdpr|lawsuit)\b", re.I)


def rule_route(ticket: str) -> str:
    """Pick a tier before calling anything. Rules are cheap, fast and predictable, and they miss things."""
    if HARD_WORDS.search(ticket) or len(ticket) > 240:
        return "large"
    return "small"


def parse_answer(text: str) -> dict[str, Any] | None:
    """The check a cascade relies on: valid JSON, a known category and enough confidence."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("category") not in CATEGORIES:
        return None
    if not isinstance(data.get("confidence"), (int, float)):
        return None
    return data


@dataclass
class Router:
    models: dict[str, LLM]
    min_confidence: float = 0.7
    spend: dict[str, float] = field(default_factory=lambda: {"small": 0.0, "large": 0.0})
    calls: dict[str, int] = field(default_factory=lambda: {"small": 0, "large": 0})

    def ask(self, tier: str, ticket: str) -> dict[str, Any] | None:
        # Room for a short answer plus any thinking; a cap that is too tight cuts the reply off (stop_reason=max_tokens).
        reply = self.models[tier].chat([user(ticket)], system=SYSTEM, max_tokens=1024)
        p_in, p_out = PRICES[tier]
        self.spend[tier] += (reply.usage.input_tokens * p_in + reply.usage.output_tokens * p_out) / 1e6
        self.calls[tier] += 1
        return parse_answer(reply.text)

    def always_large(self, ticket: str) -> tuple[str, str | None]:
        answer = self.ask("large", ticket)
        return "large", answer and answer["category"]

    def by_rules(self, ticket: str) -> tuple[str, str | None]:
        tier = rule_route(ticket)
        answer = self.ask(tier, ticket)
        return tier, answer and answer["category"]

    def cascade(self, ticket: str) -> tuple[str, str | None]:
        answer = self.ask("small", ticket)
        if answer and answer["confidence"] >= self.min_confidence:
            return "small", answer["category"]
        answer = self.ask("large", ticket)  # escalate: the small attempt's cost is already spent
        return "small->large", answer and answer["category"]

    @property
    def total(self) -> float:
        return sum(self.spend.values())


def evaluate(strategy: str) -> tuple[Router, list[tuple[str, str | None, str]]]:
    router = Router(make_models())
    rows = []
    for ticket, expected in TICKETS:
        tier, category = getattr(router, strategy)(ticket)
        rows.append((tier, category, expected))
    return router, rows


def main() -> None:
    results = {}
    for strategy in ("always_large", "by_rules", "cascade"):
        router, rows = evaluate(strategy)
        correct = sum(cat == exp for _, cat, exp in rows)
        results[strategy] = (router.total, correct)
        print(f"{strategy}:")
        for (ticket, _), (tier, cat, exp) in zip(TICKETS, rows):
            mark = "ok " if cat == exp else "BAD"
            print(f"  {mark} {tier:<13} {cat or '-':<9} {ticket[:44]}...")
        per_1000 = router.total / len(rows) * 1000
        print(f"  calls {router.calls}, correct {correct}/{len(rows)}, ${per_1000:.4f} per 1,000 tickets\n")
    base = results["always_large"][0]
    for strategy, (spent, correct) in results.items():
        print(f"{strategy:<13} {correct}/{len(TICKETS)} correct, {spent / base:.0%} of the always-large cost")


if __name__ == "__main__":
    main()
