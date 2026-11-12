"""Rule routing and a cascade between a small and a large model. Offline, with two MockLLMs."""

import json

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def router(small_script, large_script) -> "main.Router":
    return main.Router({"small": MockLLM(small_script), "large": MockLLM(large_script)})


def test_rules_send_legal_or_long_tickets_to_the_large_model() -> None:
    assert main.rule_route("Where is my parcel?") == "small"
    assert main.rule_route("I will contact a lawyer about this.") == "large"
    assert main.rule_route("x" * 300) == "large"


def test_parse_answer_rejects_bad_output() -> None:
    assert main.parse_answer('{"category": "billing", "confidence": 0.9}') == {"category": "billing", "confidence": 0.9}
    assert main.parse_answer("Sure! The category is billing.") is None
    assert main.parse_answer('{"category": "pets", "confidence": 0.9}') is None
    assert main.parse_answer('{"category": "billing"}') is None


def test_cascade_keeps_confident_small_answers() -> None:
    r = router([json.dumps({"category": "shipping", "confidence": 0.9})], [])
    assert r.cascade("Where is my parcel?") == ("small", "shipping")
    assert r.calls == {"small": 1, "large": 0}


def test_cascade_escalates_on_low_confidence_or_invalid_output() -> None:
    r = router(
        [json.dumps({"category": "billing", "confidence": 0.4}), "not json"],
        [json.dumps({"category": "legal", "confidence": 0.95})] * 2,
    )
    assert r.cascade("ticket one") == ("small->large", "legal")
    assert r.cascade("ticket two") == ("small->large", "legal")
    assert r.calls == {"small": 2, "large": 2}
    assert r.spend["small"] > 0 and r.spend["large"] > r.spend["small"]  # the failed small attempt is still paid for


def test_strategies_on_the_demo_tickets() -> None:
    results = {}
    for strategy in ("always_large", "by_rules", "cascade"):
        r, rows = main.evaluate(strategy)
        results[strategy] = (r.total, sum(cat == exp for _, cat, exp in rows), r.calls)
    assert results["always_large"][1] == 6
    assert results["by_rules"][1] == 5  # the rules miss the 'agreement' ticket
    assert results["cascade"][1] == 6  # the confidence check catches it
    assert results["by_rules"][0] < results["cascade"][0] < results["always_large"][0]
    assert results["cascade"][2] == {"small": 6, "large": 2}


def test_system_prompt_asks_for_json_with_the_categories() -> None:
    small = MockLLM([json.dumps({"category": "account", "confidence": 0.9})])
    main.Router({"small": small, "large": MockLLM([])}).by_rules("I forgot my password.")
    assert "JSON" in small.calls[0]["system"] and "legal" in small.calls[0]["system"]
    assert small.calls[0]["max_tokens"] == 1024
