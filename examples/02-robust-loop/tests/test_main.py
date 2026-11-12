"""Every stopping condition and every error path of the robust loop. Offline, with MockLLM."""

from __future__ import annotations

import pytest

from common import LLMResponse, MockLLM, ToolCall
from common.testing import load_example

main = load_example(__file__)
GOAL, TOOLS, Limits = main.GOAL, main.TOOLS, main.Limits


def run(script, **kwargs):
    llm = MockLLM(script)
    return main.run_agent(llm, GOAL, TOOLS, **kwargs), llm


def last_tool_result(llm: MockLLM, call_index: int) -> dict:
    return [m for m in llm.calls[call_index]["messages"] if m["role"] == "tool"][-1]


# --------------------------------------------------------------------------- stopping conditions (2.4)


def test_stops_on_final_answer() -> None:
    result, llm = run(["It is about 270 dollars."])
    assert (result.stopped_because, result.answer, result.steps) == ("final_answer", "It is about 270 dollars.", 1)


def test_stops_at_max_steps() -> None:
    result, llm = run([MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(10)], limits=Limits(max_steps=3))
    assert result.stopped_because == "max_steps" and result.answer is None
    assert len(llm.calls) == 3


def test_stops_on_wall_clock_timeout() -> None:
    script = [MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(10)]
    result, llm = run(script, limits=Limits(max_seconds=120), clock=main.fake_clock(50))
    assert result.stopped_because == "timeout"
    assert len(llm.calls) == 2  # checked before the third call, at t=150s


def test_stops_on_token_budget() -> None:
    script = [MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(10)]
    result, llm = run(script, limits=Limits(max_total_tokens=50))
    assert result.stopped_because == "token_budget"
    assert result.usage.input_tokens + result.usage.output_tokens >= 50
    assert len(llm.calls) < 10


def test_stops_on_cost_budget() -> None:
    script = [MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(10)]
    result, _ = run(script, limits=Limits(max_cost_usd=0.0002))
    assert result.stopped_because == "cost_budget"
    assert result.cost_usd >= 0.0002


def test_cost_uses_the_configured_prices() -> None:
    result, _ = run(["ok"], limits=Limits(input_price_per_mtok=1_000_000, output_price_per_mtok=0))
    assert result.cost_usd == result.usage.input_tokens  # $1 per input token, free output


def test_stops_when_the_same_call_repeats() -> None:
    result, llm = run([MockLLM.tool_call("get_rate", {"base": "GBP", "quote": "USD"})] * 10)
    assert result.stopped_because == "no_progress"
    assert len(llm.calls) == 3  # allowed twice, stopped on the third identical call


def test_different_arguments_are_progress() -> None:
    script = [MockLLM.tool_call("multiply", {"a": i, "b": 2}) for i in range(4)] + ["done"]
    result, _ = run(script)
    assert result.stopped_because == "final_answer"


def test_truncated_reply_is_retried_with_more_tokens_and_not_kept() -> None:
    cut = LLMResponse(text="250 euros is", stop_reason="max_tokens")
    result, llm = run([cut, "250 euros is about 270 dollars."], limits=Limits(max_output_tokens=1000))
    assert result.stopped_because == "final_answer"
    assert [c["max_tokens"] for c in llm.calls] == [1000, 2000]
    assert len(llm.calls[1]["messages"]) == 1  # the cut-off reply never entered the history


def test_truncated_tool_call_is_never_run() -> None:
    cut = LLMResponse(tool_calls=[ToolCall("c1", "multiply", {"a": 2})], stop_reason="max_tokens")
    result, llm = run([cut, cut])
    assert result.stopped_because == "max_tokens"
    assert not any(line.startswith("step") and "multiply(" in line for line in result.log)


def test_stops_on_refusal_without_running_tools() -> None:
    refusal = LLMResponse(text="I can't help with that.", stop_reason="refusal",
                          tool_calls=[ToolCall("c1", "multiply", {"a": 1, "b": 2})])
    result, llm = run([refusal])
    assert result.stopped_because == "refusal" and len(llm.calls) == 1
    assert not any("multiply(" in line for line in result.log)


# --------------------------------------------------------------------------- errors inside a step (2.5)


def test_tool_exception_becomes_error_result() -> None:
    result, llm = run([MockLLM.tool_call("get_rate", {"base": "USD", "quote": "EUR"}), "sorry"])
    msg = last_tool_result(llm, 1)
    assert msg["is_error"] is True
    assert "LookupError" in msg["content"] and "supported pairs" in msg["content"]


def test_missing_and_wrong_type_arguments_are_caught_before_running() -> None:
    result, llm = run([MockLLM.tool_call("multiply", {"a": "250", "c": 1}), "sorry"])
    content = last_tool_result(llm, 1)["content"]
    assert "missing required argument 'b'" in content
    assert "'a' must be a number, got str '250'" in content
    assert "unexpected argument 'c'" in content


def test_enum_is_enforced() -> None:
    _, llm = run([MockLLM.tool_call("get_rate", {"base": "eur", "quote": "USD"}), "sorry"])
    assert "'base' must be one of ['EUR', 'GBP', 'USD'], got 'eur'" in last_tool_result(llm, 1)["content"]


def test_unknown_tool_lists_the_real_ones() -> None:
    _, llm = run([MockLLM.tool_call("convert", {}), "sorry"])
    assert last_tool_result(llm, 1)["content"] == "Unknown tool 'convert'. Available tools: get_rate, multiply."


def test_bad_json_arguments_are_reported() -> None:
    _, llm = run([main.BAD_JSON, "sorry"])
    msg = last_tool_result(llm, 1)
    assert msg["is_error"] is True and "not valid JSON" in msg["content"]


def test_long_tool_output_is_truncated() -> None:
    big = main.Tool("dump", "Dump.", {"type": "object", "properties": {}}, lambda: "x" * 10_000)
    llm = MockLLM([MockLLM.tool_call("dump"), "ok"])
    main.run_agent(llm, GOAL, [big], limits=Limits(max_tool_output_chars=100))
    content = last_tool_result(llm, 1)["content"]
    assert content.startswith("x" * 100) and "[truncated: showing 100 of 10000 characters]" in content


def test_transient_api_errors_are_retried_with_backoff() -> None:
    delays: list[float] = []
    llm = main.FlakyLLM(MockLLM(["fine"]), failures=2)
    result = main.run_agent(llm, GOAL, TOOLS, sleep=delays.append)
    assert result.stopped_because == "final_answer"
    assert len(delays) == 2
    assert 0 <= delays[0] <= 1.0 and 0 <= delays[1] <= 2.0  # full jitter: random up to 1s, then up to 2s


def test_retries_give_up_eventually() -> None:
    llm = main.FlakyLLM(MockLLM(["never reached"]), failures=10)
    result = main.run_agent(llm, GOAL, TOOLS, limits=Limits(max_api_retries=2), sleep=lambda s: None)
    assert result.stopped_because == "api_error"


def test_permanent_errors_are_not_retried() -> None:
    class BadRequest(Exception):
        status_code = 400

    calls = []

    def fn():
        calls.append(1)
        raise BadRequest("invalid_request_error")

    with pytest.raises(BadRequest):
        main.call_with_retries(fn, max_retries=5, sleep=lambda s: None)
    assert len(calls) == 1


@pytest.mark.parametrize(("status", "expected"), [(400, False), (401, False), (404, False), (408, True),
                                                  (409, True), (429, True), (500, True), (529, True)])
def test_is_transient_by_status(status: int, expected: bool) -> None:
    err = Exception("x")
    err.status_code = status  # type: ignore[attr-defined]
    assert main.is_transient(err) is expected


def test_is_transient_with_real_sdk_exception_types() -> None:
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    rate_limited = anthropic.RateLimitError("rate limited", response=httpx2.Response(429, request=request), body=None)
    bad_request = anthropic.BadRequestError("bad", response=httpx2.Response(400, request=request), body=None)
    assert main.is_transient(rate_limited) is True
    assert main.is_transient(bad_request) is False
    assert main.is_transient(anthropic.APIConnectionError(request=request)) is True


def test_demo_run_recovers_from_every_error() -> None:
    llm = main.FlakyLLM(MockLLM(main.ERRORS_SCRIPT), failures=1)
    result = main.run_agent(llm, GOAL, TOOLS, sleep=lambda s: None)
    assert result.stopped_because == "final_answer" and "270" in (result.answer or "")
    assert sum("ERROR" in line for line in result.log) == 4
