"""Routing: classify, validate the label, dispatch to the right prompt and model. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def setup(classifier_reply: str):
    classifier = MockLLM([classifier_reply])
    small, large = MockLLM(["small answer"]), MockLLM(["large answer"])
    return classifier, {"small": small, "large": large}, small, large


def test_easy_billing_goes_to_small_model_with_billing_prompt() -> None:
    classifier, models, small, large = setup('{"category": "billing", "difficulty": "easy"}')
    r = main.route_ticket("charged twice", classifier, models)
    assert r.answer == "small answer" and r.tier == "small"
    assert small.calls[0]["system"] == main.CATEGORIES["billing"]
    assert large.calls == []  # the expensive model was never called


def test_hard_technical_goes_to_large_model() -> None:
    classifier, models, small, large = setup('{"category": "technical", "difficulty": "hard"}')
    r = main.route_ticket("app crashes", classifier, models)
    assert r.tier == "large" and small.calls == []
    assert large.calls[0]["system"] == main.CATEGORIES["technical"]


def test_classifier_gets_its_own_prompt_and_the_ticket() -> None:
    classifier, models, _, _ = setup('{"category": "general", "difficulty": "easy"}')
    main.route_ticket("hello?", classifier, models)
    assert classifier.calls[0]["system"] == main.CLASSIFIER_SYSTEM
    assert classifier.calls[0]["messages"][0]["content"] == "hello?"


def test_small_slips_are_normalised() -> None:
    route = main.parse_route('{"category": " Billing. ", "difficulty": "EASY"}')
    assert (route.category, route.difficulty, route.valid) == ("billing", "easy", True)


def test_unknown_or_broken_labels_fall_back_safely() -> None:
    unknown = main.parse_route('{"category": "sales", "difficulty": "easy"}')
    assert unknown.category == main.FALLBACK_CATEGORY and not unknown.valid
    broken = main.parse_route("I think this is billing")
    assert (broken.category, broken.difficulty, broken.valid) == ("general", "hard", False)
    not_a_dict = main.parse_route('["billing"]')
    assert not not_a_dict.valid


def test_demo_routes_all_three_tickets() -> None:
    classifier = MockLLM([main.mock_classifier] * 3)
    models = {"small": MockLLM([main.mock_answer] * 3), "large": MockLLM([main.mock_answer] * 3)}
    tiers = [main.route_ticket(t, classifier, models).tier for t in main.TICKETS]
    assert tiers == ["small", "large", "small"]
