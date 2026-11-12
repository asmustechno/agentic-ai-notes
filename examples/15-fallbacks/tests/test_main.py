"""Token bucket, circuit breaker and fallback chain. Offline, with MockLLM and a fake clock."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from common import MockLLM, user
from common.testing import load_example

main = load_example(__file__)


def quiet(_msg: str) -> None:
    pass


def chain(clock: main.FakeClock, primary_fail, *, threshold: int = 3, **kwargs) -> tuple[main.FallbackLLM, main.FlakyLLM, MockLLM]:
    primary = main.FlakyLLM(MockLLM([main.answer_as("a")] * 20), clock, primary_fail)
    backup = MockLLM([main.answer_as("b")] * 20)
    llm = main.FallbackLLM(
        [
            main.Provider("a", primary, main.CircuitBreaker(failure_threshold=threshold, reset_after=30, clock=clock)),
            main.Provider("b", backup, main.CircuitBreaker(clock=clock)),
        ],
        sleep=clock.sleep, rng=lambda: 0.5, log=quiet, **kwargs,
    )
    return llm, primary, backup


def test_healthy_primary_serves_everything() -> None:
    llm, _, backup = chain(main.FakeClock(), lambda now: None)
    assert llm.chat([user("hi")]).text == "[a] answer to 'hi'"
    assert backup.calls == []


def test_overloaded_primary_falls_back_after_retries() -> None:
    llm, primary, backup = chain(main.FakeClock(), lambda now: main.ProviderError(529, "overloaded"), retries_per_provider=1)
    assert llm.chat([user("hi")]).text.startswith("[b]")
    assert primary.calls == 2  # first try + one retry
    assert backup.calls[0]["messages"][0]["content"] == "hi"  # the same request went to the backup


def test_circuit_opens_then_skips_primary() -> None:
    llm, primary, _ = chain(main.FakeClock(), lambda now: main.ProviderError(503), retries_per_provider=0, threshold=2)
    for _ in range(5):
        llm.chat([user("q")])
    assert primary.calls == 2  # after 2 failures the circuit opened; the rest never touched it
    assert llm.served_by == ["b"] * 5


def test_half_open_trial_call_closes_circuit_on_success() -> None:
    clock = main.FakeClock()
    llm, primary, _ = chain(clock, lambda now: main.ProviderError(503) if now < 10 else None,
                            retries_per_provider=0, threshold=1)
    llm.chat([user("q1")])  # fails, opens
    clock.now = 15
    llm.chat([user("q2")])  # still open (opened at 0, reset after 30)
    assert primary.calls == 1
    clock.now = 31
    assert llm.chat([user("q3")]).text.startswith("[a]")  # trial call succeeds
    assert llm.providers[0].breaker.state == "closed"


def test_breaker_state_machine() -> None:
    clock = main.FakeClock()
    b = main.CircuitBreaker(failure_threshold=2, reset_after=10, clock=clock)
    b.record_failure()
    assert b.state == "closed" and b.allow()
    b.record_failure()
    assert b.state == "open" and not b.allow()
    clock.now = 10
    assert b.allow() and b.state == "half_open"
    b.record_failure()  # the trial failed
    assert b.state == "open" and not b.allow()
    clock.now = 20
    assert b.allow()
    b.record_success()
    assert b.state == "closed" and b.failures == 0


def test_rate_limit_waits_for_retry_after_and_stays_on_primary() -> None:
    clock = main.FakeClock()
    errors = iter([main.ProviderError(429, retry_after=3.0)])
    llm, primary, backup = chain(clock, lambda now: next(errors, None), retries_per_provider=1)
    assert llm.chat([user("q")]).text.startswith("[a]")
    assert clock.now == 3.0 and backup.calls == []


def test_retry_after_longer_than_max_wait_falls_back_immediately() -> None:
    clock = main.FakeClock()
    llm, _, _ = chain(clock, lambda now: main.ProviderError(429, retry_after=60.0), retries_per_provider=3, max_wait=10)
    assert llm.chat([user("q")]).text.startswith("[b]")
    assert clock.now == 0.0  # did not sit and wait a minute


def test_bad_request_is_raised_not_fallen_back() -> None:
    llm, _, backup = chain(main.FakeClock(), lambda now: main.ProviderError(400, "bad request"))
    with pytest.raises(main.ProviderError):
        llm.chat([user("q")])
    assert backup.calls == []  # another provider would reject a broken request too


def test_all_providers_down_raises() -> None:
    clock = main.FakeClock()
    down = main.FlakyLLM(MockLLM([]), clock, lambda now: main.ProviderError(500))
    llm = main.FallbackLLM([main.Provider("a", down, main.CircuitBreaker(clock=clock))], sleep=clock.sleep, log=quiet)
    with pytest.raises(main.AllProvidersFailed):
        llm.chat([user("q")])


def test_refusal_fallback_is_opt_in() -> None:
    refusing = MockLLM([main.LLMResponse(text="I can't help with that.", stop_reason="refusal")] * 2)
    backup = MockLLM(["[b] ok"] * 2)
    off = main.FallbackLLM([main.Provider("a", refusing), main.Provider("b", backup)], log=quiet)
    assert off.chat([user("q")]).stop_reason == "refusal"
    on = main.FallbackLLM([main.Provider("a", refusing), main.Provider("b", backup)], fallback_on_refusal=True, log=quiet)
    assert on.chat([user("q")]).text == "[b] ok"


def test_token_bucket_allows_burst_then_paces() -> None:
    clock = main.FakeClock()
    bucket = main.TokenBucket(rate=2.0, capacity=2, clock=clock, sleep=clock.sleep)
    waits = [bucket.acquire() for _ in range(4)]
    assert waits == [0.0, 0.0, 0.5, 0.5]
    clock.now += 10  # idle time refills, but never above capacity
    assert [bucket.acquire() for _ in range(3)] == [0.0, 0.0, 0.5]


def test_error_classification_and_retry_after_header() -> None:
    assert main.is_retryable(main.ProviderError(529))
    assert main.is_retryable(TimeoutError())
    assert not main.is_retryable(main.ProviderError(401))
    sdk_style = SimpleNamespace(status_code=429, response=SimpleNamespace(headers={"retry-after": "4"}))
    assert main.retry_after_seconds(sdk_style) == 4.0  # type: ignore[arg-type]
    assert main.retry_after_seconds(SimpleNamespace(response=SimpleNamespace(headers={}))) is None  # type: ignore[arg-type]


def test_real_sdk_exceptions_are_classified() -> None:
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx2.Response(429, request=req, headers={"retry-after": "5"})
    exc = anthropic.RateLimitError("rate limited", response=resp, body=None)
    assert main.is_retryable(exc) and main.retry_after_seconds(exc) == 5.0
    assert main.is_retryable(anthropic.APITimeoutError(request=req))
    bad = anthropic.BadRequestError("bad", response=httpx2.Response(400, request=req), body=None)
    assert not main.is_retryable(bad)


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    main.main()
    out = capsys.readouterr().out
    assert "served by: ['openai', 'openai', 'openai', 'openai', 'anthropic', 'anthropic']" in out
    assert "circuit open, skipped" in out
