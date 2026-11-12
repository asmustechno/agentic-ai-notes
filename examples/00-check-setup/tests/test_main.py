"""Tests for the setup check. Offline, with MockLLM."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_check_reports_provider_model_and_reply() -> None:
    llm = MockLLM(["Hi there!"])
    report = main.check(llm)
    assert "Provider: mock" in report
    assert "Model:    mock-model" in report
    assert "Reply:    Hi there!" in report
    assert len(llm.calls) == 1
