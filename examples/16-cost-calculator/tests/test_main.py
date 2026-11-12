"""Cost maths: one call, a whole run, and the quadratic growth of an agent loop."""

import pytest

from common import MockLLM, Usage, user
from common.testing import load_example

main = load_example(__file__)


def test_single_call_cost_matches_the_price_list() -> None:
    opus = main.PRICES["claude-opus-5-5"]
    # 1M input at $4 + 1M output at $20
    assert main.call_cost(opus, 1_000_000, 1_000_000) == pytest.approx(24.0)
    assert main.call_cost(opus, 2_000, 500) == pytest.approx(0.018)
    haiku = main.PRICES["claude-haiku-5-5"]
    assert main.call_cost(haiku, 2_000, 500) == pytest.approx(0.00045)


def test_cached_tokens_are_priced_separately() -> None:
    opus = main.PRICES["claude-opus-5-5"]
    # 100k read from cache at $0.20/M + 10k written at $5/M + 1k uncached at $4/M
    cost = main.call_cost(opus, 1_000, 0, cache_read=100_000, cache_write=10_000)
    assert cost == pytest.approx((1_000 * 4 + 100_000 * 0.20 + 10_000 * 5) / 1e6)


def test_loop_resends_the_conversation() -> None:
    shape = main.LoopShape(fixed=1000, goal=0, output=100, tool_result=400)
    usages = main.loop_usage(shape, 3)
    assert [u.input_tokens for u in usages] == [1000, 1500, 2000]
    assert sum(u.input_tokens for u in usages) == main.loop_input_closed_form(shape, 3)


@pytest.mark.parametrize("steps", [1, 2, 7, 10, 40])
def test_closed_form_matches_simulation(steps: int) -> None:
    shape = main.LoopShape()
    assert sum(u.input_tokens for u in main.loop_usage(shape, steps)) == main.loop_input_closed_form(shape, steps)


def test_cost_grows_faster_than_steps() -> None:
    opus = main.PRICES["claude-opus-5-5"]
    shape = main.LoopShape()
    c10 = main.run_cost(opus, main.loop_usage(shape, 10))
    c20 = main.run_cost(opus, main.loop_usage(shape, 20))
    assert c10 == pytest.approx(0.344)
    assert c20 / c10 > 3


def test_run_cost_from_real_usage_records() -> None:
    llm = MockLLM(["hello"])
    reply = llm.chat([user("hi")])
    sonnet = main.PRICES["claude-sonnet-5-5"]
    assert main.run_cost(sonnet, [reply.usage]) == pytest.approx(
        (reply.usage.input_tokens * 2 + reply.usage.output_tokens * 10) / 1e6
    )
    assert main.run_cost(sonnet, [Usage(0, 0)]) == 0


def test_openai_price_only_from_environment(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_INPUT_PRICE", raising=False)
    monkeypatch.delenv("OPENAI_OUTPUT_PRICE", raising=False)
    assert main.openai_price_from_env() is None
    monkeypatch.setenv("OPENAI_INPUT_PRICE", "1.5")
    monkeypatch.setenv("OPENAI_OUTPUT_PRICE", "6")
    assert main.openai_price_from_env() == main.Price(input=1.5, output=6.0)
