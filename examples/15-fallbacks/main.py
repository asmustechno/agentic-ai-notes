"""Stay up when a provider is slow, busy or down: a token bucket, a circuit breaker and a fallback chain.

    python main.py                  # from this folder
    python 15-fallbacks/main.py     # from examples/

Read alongside docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md.

The demo simulates an outage on the primary provider with a fake clock, so it
runs instantly and gives the same output every time. `build_real_chain()` shows
how to wire the same FallbackLLM to real Anthropic and OpenAI clients.
"""

from __future__ import annotations

import random
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, user  # noqa: E402
from common.llm import DEFAULT_MAX_TOKENS  # noqa: E402

# --------------------------------------------------------------------------- errors: what to retry, what to fall back on


class ProviderError(Exception):
    """A simulated API error, shaped like the SDKs' APIStatusError (it has .status_code)."""

    def __init__(self, status_code: int, message: str = "", retry_after: float | None = None) -> None:
        super().__init__(f"{status_code} {message}".strip())
        self.status_code = status_code
        self.retry_after = retry_after


def is_retryable(exc: BaseException) -> bool:
    """Timeouts, connection errors, 408/409/429 and 5xx (including Anthropic's 529 overloaded).

    Works for the real SDK exceptions too: anthropic/openai APIStatusError subclasses
    carry .status_code, and APIConnectionError / APITimeoutError carry none.
    """
    if isinstance(exc, (TimeoutError, ConnectionError)) or type(exc).__name__ in ("APIConnectionError", "APITimeoutError"):
        return True
    status = getattr(exc, "status_code", None)
    return status is not None and (status in (408, 409, 429) or status >= 500)


def retry_after_seconds(exc: BaseException) -> float | None:
    """How long the server asked us to wait, from .retry_after or the response's Retry-After header."""
    if getattr(exc, "retry_after", None) is not None:
        return float(exc.retry_after)  # type: ignore[attr-defined]
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    value = headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None  # an HTTP-date; treat as "no hint"


# --------------------------------------------------------------------------- client-side rate limiting


class TokenBucket:
    """Allow `rate` requests per second on average, with bursts of up to `capacity`.

    The bucket refills continuously. Each request takes one token; if none is
    left, the caller waits until one has dripped back in. Staying under your
    provider's limit on the client side means fewer 429s to handle.
    """

    def __init__(self, rate: float, capacity: float, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.rate, self.capacity, self.clock, self.sleep = rate, capacity, clock, sleep
        self.tokens, self.updated = capacity, clock()
        self.lock = threading.Lock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def acquire(self, n: float = 1.0) -> float:
        """Take `n` tokens, sleeping if needed. Returns how long we waited."""
        with self.lock:
            self._refill()
            wait = 0.0 if self.tokens >= n else (n - self.tokens) / self.rate
            if wait:
                self.sleep(wait)
                self._refill()
            self.tokens -= n
            return wait


# --------------------------------------------------------------------------- circuit breaker


class CircuitBreaker:
    """Stop calling a provider that keeps failing, then test it again after a cool-down.

    closed    -> calls go through; count consecutive failures
    open      -> calls are skipped at once (fail fast, go to the fallback)
    half_open -> after `reset_after` seconds, let one trial call through:
                 success closes the circuit, failure opens it again
    """

    def __init__(self, failure_threshold: int = 3, reset_after: float = 30.0, *,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.failure_threshold, self.reset_after, self.clock = failure_threshold, reset_after, clock
        self.state, self.failures, self.opened_at = "closed", 0, 0.0

    def allow(self) -> bool:
        if self.state == "open" and self.clock() - self.opened_at >= self.reset_after:
            self.state = "half_open"  # time for one trial call
        return self.state != "open"

    def record_success(self) -> None:
        self.state, self.failures = "closed", 0

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state, self.opened_at = "open", self.clock()


# --------------------------------------------------------------------------- the fallback chain


@dataclass
class Provider:
    name: str
    llm: LLM
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    bucket: TokenBucket | None = None


class AllProvidersFailed(RuntimeError):
    """Every provider in the chain was skipped or failed."""


class FallbackLLM(LLM):
    """An LLM that tries providers in order. Agent code uses it like any other LLM.

    For each provider: skip it if its circuit is open; wait for its token bucket;
    retry retryable errors a few times (honouring Retry-After); then move on.
    Non-retryable errors (400, 401, 404...) are raised at once: they are bugs in
    the request, and another provider would not fix them.
    """

    provider = "fallback"

    def __init__(self, providers: list[Provider], *, retries_per_provider: int = 1, max_wait: float = 10.0,
                 fallback_on_refusal: bool = False, sleep: Callable[[float], None] = time.sleep,
                 rng: Callable[[], float] = random.random, log: Callable[[str], None] = print) -> None:
        self.providers, self.retries, self.max_wait = providers, retries_per_provider, max_wait
        self.fallback_on_refusal, self.sleep, self.rng, self.log = fallback_on_refusal, sleep, rng, log
        self.served_by: list[str] = []  # which provider answered each call (log this in production)

    def chat(self, messages: list[Message], *, system: str | None = None, tools: list[ToolSpec] | None = None,
             max_tokens: int = DEFAULT_MAX_TOKENS) -> LLMResponse:
        for p in self.providers:
            if not p.breaker.allow():
                self.log(f"    {p.name}: circuit open, skipped")
                continue
            if p.breaker.state == "half_open":
                self.log(f"    {p.name}: circuit half-open, sending one trial call")
            if p.bucket and (waited := p.bucket.acquire()):
                self.log(f"    {p.name}: rate limiter waited {waited:.1f}s")
            for attempt in range(self.retries + 1):
                try:
                    reply = p.llm.chat(messages, system=system, tools=tools, max_tokens=max_tokens)
                except Exception as exc:
                    if not is_retryable(exc):
                        raise
                    p.breaker.record_failure()
                    hint = retry_after_seconds(exc)
                    wait = hint if hint is not None else min(self.max_wait, 0.5 * 2**attempt) * self.rng()
                    last = attempt == self.retries or p.breaker.state == "open" or wait > self.max_wait
                    self.log(f"    {p.name}: {exc} -> {'fall back' if last else f'retry in {wait:.1f}s'}"
                             f" (circuit {p.breaker.state})")
                    if last:
                        break
                    self.sleep(wait)
                    continue
                p.breaker.record_success()
                if reply.stop_reason == "refusal" and self.fallback_on_refusal and p is not self.providers[-1]:
                    self.log(f"    {p.name}: refused -> fall back")
                    break
                self.served_by.append(p.name)
                return reply
        raise AllProvidersFailed("every provider was skipped or failed")


def build_real_chain() -> FallbackLLM:
    """The same chain with real clients (needs ANTHROPIC_API_KEY, OPENAI_API_KEY and OPENAI_MODEL).

    max_retries=0 turns off the SDKs' own retries so they don't multiply with ours
    (each SDK retries twice by default). Keep one layer in charge of retrying.
    """
    import anthropic
    import openai

    from common import AnthropicLLM, OpenAILLM

    return FallbackLLM([
        Provider("anthropic", AnthropicLLM(client=anthropic.Anthropic(max_retries=0)), bucket=TokenBucket(rate=5, capacity=10)),
        Provider("openai", OpenAILLM(client=openai.OpenAI(max_retries=0)), bucket=TokenBucket(rate=5, capacity=10)),
    ])


# --------------------------------------------------------------------------- simulation helpers


class FakeClock:
    """Time that only moves when we say so. sleep() advances it instantly."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class FlakyLLM(LLM):
    """Wraps an LLM and raises a scripted error while `fail_when(now)` returns one."""

    inner: LLM
    clock: Callable[[], float]
    fail_when: Callable[[float], Exception | None]
    provider: str = "flaky"
    calls: int = 0

    def chat(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        self.calls += 1
        if (err := self.fail_when(self.clock())) is not None:
            raise err
        return self.inner.chat(messages, **kwargs)


def answer_as(name: str) -> Callable[[list[Message]], str]:
    return lambda messages: f"[{name}] answer to {messages[-1]['content']!r}"


def primary_outage(now: float) -> Exception | None:
    """The primary is overloaded from t=0 to t=60s, rate-limits once at t=90s, then is fine."""
    if now < 60:
        return ProviderError(529, "overloaded_error")
    if 90 <= now < 91:
        return ProviderError(429, "rate_limit_error", retry_after=2.0)
    return None


def main() -> None:
    clock = FakeClock()
    primary = FlakyLLM(MockLLM([answer_as("anthropic")] * 20), clock, primary_outage)
    secondary = MockLLM([answer_as("openai")] * 20)
    llm = FallbackLLM(
        [
            Provider("anthropic", primary, CircuitBreaker(failure_threshold=3, reset_after=30, clock=clock)),
            Provider("openai", secondary, CircuitBreaker(clock=clock)),
        ],
        retries_per_provider=1,
        sleep=clock.sleep,
        rng=random.Random(3).random,
    )

    print("1) Requests during and after an outage of the primary provider")
    for t in [0, 10, 20, 40, 70, 90]:
        clock.now = max(clock.now, float(t))
        print(f"  t={clock.now:5.1f}s  request #{len(llm.served_by) + 1}")
        reply = llm.chat([user(f"question {len(llm.served_by) + 1}")])
        print(f"    -> {reply.text}")
    print(f"\n  served by: {llm.served_by}")
    print(f"  calls that reached the primary: {primary.calls} (the open circuit saved the rest)")

    print("\n2) Client-side token bucket: 1 request/s, bursts of 3")
    clock2 = FakeClock()
    bucket = TokenBucket(rate=1.0, capacity=3, clock=clock2, sleep=clock2.sleep)
    for i in range(6):
        waited = bucket.acquire()
        print(f"  request {i + 1} sent at t={clock2.now:.1f}s (waited {waited:.1f}s)")


if __name__ == "__main__":
    main()
