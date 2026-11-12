"""Cache-friendly request layout: stable prefix first, volatile parts last, and the savings that follow."""

from datetime import datetime

from common import user
from common.testing import load_example

main = load_example(__file__)
T0 = datetime(2026, 11, 13, 9, 30, 0)
T1 = datetime(2026, 11, 13, 9, 30, 7)


def test_cached_layout_orders_tools_and_freezes_the_system_prompt() -> None:
    req = main.build_request_cached([user("hi")], "Ana", T0)
    assert [t["name"] for t in req["tools"]] == sorted(t["name"] for t in main.TOOLS)
    assert req["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert req["system"][-1]["text"] == main.SYSTEM_STATIC  # nothing per-request in it
    assert req["cache_control"] == {"type": "ephemeral"}  # automatic caching for the conversation tail
    first = req["messages"][0]["content"]
    assert "Customer: Ana" in first[0]["text"] and first[1]["text"] == "hi"


def test_two_requests_share_their_prefix_only_in_the_cached_layout() -> None:
    a = main.build_request_cached([user("hi")], "Ana", T0)
    b = main.build_request_cached([user("hi")], "Ana", T1)
    assert main.first_divergence(a, b) is None
    a = main.build_request_naive([user("hi")], "Ana", T0)
    b = main.build_request_naive([user("hi")], "Ana", T1)
    assert "Current time" in main.first_divergence(a, b)


def test_simulated_cache_reads_the_previous_prefix() -> None:
    usages, _, _ = main.simulate_run(main.build_request_cached, T0)
    assert usages[0]["cache_read_input_tokens"] == 0 and usages[0]["cache_creation_input_tokens"] > 3000
    for prev, cur in zip(usages, usages[1:]):
        # healthy loop: each call reads everything the previous one wrote, and writes only the new tail
        prev_total = prev["cache_read_input_tokens"] + prev["cache_creation_input_tokens"]
        assert cur["cache_read_input_tokens"] == prev_total
        assert cur["cache_creation_input_tokens"] < 200


def test_naive_layout_never_reads_and_costs_more_than_no_caching() -> None:
    usages, _, out = main.simulate_run(main.build_request_naive, T0)
    assert all(u["cache_read_input_tokens"] == 0 for u in usages)
    with_cache = sum(main.cost(u, 0) for u in usages)
    without = sum(main.cost({"input_tokens": sum(u.values()), "cache_read_input_tokens": 0,
                             "cache_creation_input_tokens": 0}, 0) for u in usages)
    assert with_cache > without  # paying the 1.25x write premium every time, reading nothing


def test_prefix_below_the_minimum_is_not_cached() -> None:
    cache = main.SimulatedCache()
    tiny = {"system": [{"type": "text", "text": "Be brief.", "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": "hi"}]}
    for _ in range(2):
        u = cache.send(tiny)
        assert u["cache_read_input_tokens"] == 0 and u["cache_creation_input_tokens"] == 0


def test_cost_uses_the_cache_prices() -> None:
    u = {"input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000}
    assert round(main.cost(u, 1_000_000), 2) == round(4.00 + 5.00 + 0.20 + 20.00, 2)
