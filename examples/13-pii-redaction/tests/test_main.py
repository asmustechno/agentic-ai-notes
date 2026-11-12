"""Redaction finds what it should, leaves the rest, and keeps PII out of prompts and logs. Offline."""

import logging

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_luhn() -> None:
    assert main.luhn_ok("4242 4242 4242 4242")
    assert main.luhn_ok("5555-5555-5555-4444")
    assert not main.luhn_ok("4242 4242 4242 4241")
    assert not main.luhn_ok("1234567890123")


def test_redacts_each_kind_and_reuses_placeholders() -> None:
    r = main.Redactor()
    out = r.redact("ada@example.com or ada@example.com, +44 7700 900123, 4242 4242 4242 4242")
    assert out == "<EMAIL_1> or <EMAIL_1>, <PHONE_1>, <CARD_1>"
    assert r.mapping["<EMAIL_1>"] == "ada@example.com"


def test_secrets_are_caught() -> None:
    r = main.Redactor()
    text = "keys: sk-ant-api03-" + "a" * 30 + " AKIAABCDEFGHIJKLMNOP ghp_" + "b" * 36
    assert r.redact(text) == "keys: <API_KEY_1> <API_KEY_2> <API_KEY_3>"


def test_leaves_ordinary_numbers_alone() -> None:
    r = main.Redactor()
    text = "Order 1234567890123 shipped on 2026-11-13, total 42.50."
    assert r.redact(text) == text and r.mapping == {}


def test_restore_brings_back_contacts_but_masks_cards_and_keys() -> None:
    r = main.Redactor()
    safe = r.redact("ada@example.com paid with 4242 4242 4242 4242 using sk-" + "z" * 24)
    assert r.restore(safe) == "ada@example.com paid with card ending 4242 using [API_KEY]"
    assert r.restore(safe, kinds=frozenset({"CARD"})).count("4242 4242 4242 4242") == 1


def test_logging_filter_scrubs_records(caplog) -> None:
    log = logging.getLogger("test-redact")
    log.addFilter(main.RedactingFilter())
    with caplog.at_level(logging.INFO, logger="test-redact"):
        log.info("user %s card %s", "ada@example.com", "4242 4242 4242 4242")
    assert caplog.messages == ["user [EMAIL] card [CARD]"]


def test_model_only_sees_placeholders_and_tool_gets_real_address() -> None:
    main.SENT.clear()
    llm = MockLLM(main.SCRIPT)
    answer = main.run_agent(llm, main.MESSAGE, main.Redactor(), logging.getLogger("quiet"))
    sent_to_model = str([c["messages"] for c in llm.calls]) + str(llm.calls[0]["system"])
    for secret in ("ada@example.com", "7700 900123", "4242 4242 4242 4242"):
        assert secret not in sent_to_model
    assert main.SENT == [{"to": "ada@example.com", "body": main.SENT[0]["body"]}]
    assert "4242 4242 4242 4242" not in main.SENT[0]["body"]  # cards are never restored
    assert "ada@example.com" in answer
