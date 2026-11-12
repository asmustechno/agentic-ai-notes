"""Routing: classify the input, validate the label, then dispatch to a specialised handler.

    ticket -> [classifier: small model] -> {"category", "difficulty"}  -> validate
           -> category picks the handler prompt
           -> difficulty picks the model: easy -> small and cheap, hard -> large and capable

An invalid or unknown label never crashes the app and never reaches a handler unchecked:
it falls back to a safe default route, and the fallback is recorded.

    python main.py               # from this folder
    python 09-routing/main.py    # from examples/

Read alongside docs/09-agent-design-patterns/09.2-routing.md.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, AnthropicLLM, Message, MockLLM, OpenAILLM, get_llm, user  # noqa: E402

CATEGORIES = {
    "billing": "You handle billing questions for a budgeting app. Be precise about money. Never promise refunds; "
    "say a billing specialist will confirm.",
    "technical": "You are a senior support engineer for a budgeting app. Ask for exactly the details you need "
    "and give numbered troubleshooting steps.",
    "general": "You answer general questions about a budgeting app in two or three friendly sentences.",
}
DIFFICULTIES = {"easy": "small", "hard": "large"}  # difficulty -> model tier
FALLBACK_CATEGORY, FALLBACK_DIFFICULTY = "general", "hard"  # when unsure, use the safer, more capable path

CLASSIFIER_SYSTEM = (
    "Classify a customer support ticket. Reply with JSON only: "
    '{"category": "billing" | "technical" | "general", "difficulty": "easy" | "hard"}. '
    "'hard' means it needs investigation or several steps; 'easy' means a short factual answer."
)


@dataclass
class Route:
    category: str
    difficulty: str
    valid: bool  # False if the classifier's label had to be replaced by the fallback
    raw_label: str


@dataclass
class Routed:
    route: Route
    tier: str
    answer: str


def parse_route(text: str) -> Route:
    """Validate the classifier's reply. Normalise small slips; replace anything unknown with the fallback."""
    try:
        data = json.loads(text)
        category = str(data.get("category", "")).strip().strip(".").lower()
        difficulty = str(data.get("difficulty", "")).strip().strip(".").lower()
    except (json.JSONDecodeError, AttributeError):
        return Route(FALLBACK_CATEGORY, FALLBACK_DIFFICULTY, False, text)
    valid = category in CATEGORIES and difficulty in DIFFICULTIES
    return Route(
        category if category in CATEGORIES else FALLBACK_CATEGORY,
        difficulty if difficulty in DIFFICULTIES else FALLBACK_DIFFICULTY,
        valid,
        text,
    )


def route_ticket(ticket: str, classifier: LLM, models: dict[str, LLM]) -> Routed:
    """Classify, validate, dispatch."""
    route = parse_route(classifier.chat([user(ticket)], system=CLASSIFIER_SYSTEM).text)
    tier = DIFFICULTIES[route.difficulty]
    answer = models[tier].chat([user(ticket)], system=CATEGORIES[route.category]).text
    return Routed(route, tier, answer)


# ---------------------------------------------------------------- an offline demo

TICKETS = [
    "I was charged twice for my March subscription. Can you fix it?",
    "Since updating to 2.3, the Android app crashes every time I sync my bank. I've reinstalled twice.",
    "Do you offer a student discount?",
]


def mock_classifier(messages: list[Message]) -> str:
    """Stands in for a small classification model, including one off-list label to show validation."""
    text = messages[-1]["content"].lower()
    if "charged" in text:
        return '{"category": "Billing", "difficulty": "easy"}'  # capitalised: normalised, still valid
    if "crash" in text:
        return '{"category": "technical", "difficulty": "hard"}'
    return '{"category": "sales", "difficulty": "easy"}'  # not one of our categories -> fallback


MOCK_ANSWERS = {
    "charged": "Sorry about the double charge. I've passed this to a billing specialist, who will check "
    "your March payments and confirm the refund of any duplicate.",
    "crash": "Thanks for the details. 1) Tell me your Android version. 2) Open Settings > Sync and note the "
    "bank name. 3) Turn off battery optimisation for the app and try once more.",
    "student": "I can't confirm discounts from here. You can see every current plan under Settings > Plans, "
    "and our sales team can tell you about any student offers.",
}


def mock_answer(messages: list[Message]) -> str:
    text = messages[-1]["content"].lower()
    return next(answer for key, answer in MOCK_ANSWERS.items() if key in text)


def make_models() -> tuple[LLM, dict[str, LLM]]:
    """Return (classifier, {"small": ..., "large": ...}) for the provider in LLM_PROVIDER."""
    default = get_llm(mock_responses=[mock_classifier] * len(TICKETS))  # also loads examples/.env
    if default.provider == "anthropic":
        small = AnthropicLLM(model=os.getenv("ANTHROPIC_SMALL_MODEL", "claude-haiku-5-5"))
        return small, {"small": small, "large": default}
    if default.provider == "openai":
        small = OpenAILLM(model=os.getenv("OPENAI_SMALL_MODEL") or None)  # falls back to OPENAI_MODEL
        return small, {"small": small, "large": default}
    return default, {"small": MockLLM([mock_answer] * 3), "large": MockLLM([mock_answer] * 3)}


def main() -> None:
    classifier, models = make_models()
    for ticket in TICKETS:
        r = route_ticket(ticket, classifier, models)
        flag = "" if r.route.valid else f"   [invalid label {r.route.raw_label}, used fallback]"
        print(f"Ticket: {ticket}")
        print(f"  route -> {r.route.category} / {r.route.difficulty} -> {r.tier} model{flag}")
        print(f"  reply -> {r.answer}\n")


if __name__ == "__main__":
    main()
