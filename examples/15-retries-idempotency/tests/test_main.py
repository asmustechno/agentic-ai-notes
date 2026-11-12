"""Retries, idempotency keys and the dead-letter queue. Offline, with MockLLM and a fake sleep."""

from __future__ import annotations

import random

import pytest

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def no_sleep(_seconds: float) -> None:
    pass


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503, 529])
def test_transient_statuses_are_retryable(status: int) -> None:
    assert main.is_retryable(main.APIError(status))


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422])
def test_client_errors_are_not_retryable(status: int) -> None:
    assert not main.is_retryable(main.APIError(status))


def test_timeouts_and_connection_errors_are_retryable() -> None:
    assert main.is_retryable(TimeoutError())
    assert main.is_retryable(ConnectionError())
    assert not main.is_retryable(ValueError("bug in our code"))


def test_backoff_grows_and_is_capped() -> None:
    always_max = lambda: 1.0  # noqa: E731  (the top of the jitter range)
    delays = [main.backoff_delay(a, base=0.5, cap=4.0, rng=always_max) for a in range(6)]
    assert delays == [0.5, 1.0, 2.0, 4.0, 4.0, 4.0]
    rng = random.Random(1).random
    assert all(0 <= main.backoff_delay(a, rng=rng) <= min(30.0, 0.5 * 2**a) for a in range(10))


def test_retry_honours_retry_after_and_stops_on_permanent_errors() -> None:
    waits: list[float] = []
    attempts = iter([main.APIError(429, retry_after=7.0), "ok"])

    def flaky() -> str:
        item = next(attempts)
        if isinstance(item, Exception):
            raise item
        return item

    assert main.retry(flaky, sleep=waits.append, log=lambda _: None) == "ok"
    assert waits == [7.0]  # the server's Retry-After, not our own backoff

    calls = 0

    def bad_request() -> None:
        nonlocal calls
        calls += 1
        raise main.APIError(400, "bad")

    with pytest.raises(main.APIError):
        main.retry(bad_request, sleep=no_sleep, log=lambda _: None)
    assert calls == 1  # never retried


def test_retry_gives_up_after_max_attempts() -> None:
    api = main.FlakyPaymentsAPI(lose_responses=10)
    with pytest.raises(TimeoutError):
        main.retry(lambda: api.refund("A-1001", 1.0, idempotency_key="k"), max_attempts=3, sleep=no_sleep, log=lambda _: None)
    assert len(api.refunds) == 1  # the key kept every retry from refunding again


def test_lost_response_without_key_refunds_twice() -> None:
    api = main.FlakyPaymentsAPI(lose_responses=1)
    main.refund_with_retries(api, "A-1001", 20.0, key=None, sleep=no_sleep, rng=lambda: 0.0)
    assert len(api.refunds) == 2  # the bug idempotency keys exist to prevent


def test_lost_response_with_key_refunds_once_and_returns_first_result() -> None:
    api = main.FlakyPaymentsAPI(lose_responses=1)
    out = main.refund_with_retries(api, "A-1001", 20.0, key="k1", sleep=no_sleep, rng=lambda: 0.0)
    assert len(api.refunds) == 1
    assert out == api.refunds[0]


def test_redelivered_agent_job_refunds_once() -> None:
    api = main.FlakyPaymentsAPI()
    queue = main.InMemoryQueue()
    queue.send(main.Job("job-1", "Refund order A-1001 for 20.00 GBP."))
    llm = MockLLM([main.refund_agent_mock] * 4)
    main.run_worker(
        queue,
        lambda job: main.run_refund_agent(llm, api, job, sleep=no_sleep, rng=lambda: 0.0),
        crash_once_after={"job-1"},
        log=lambda _: None,
    )
    assert len(llm.calls) == 4  # the agent ran twice (2 model calls each)...
    assert len(api.refunds) == 1  # ...but the money moved once
    assert [j.id for j in queue.done] == ["job-1"] and queue.done[0].deliveries == 2
    assert llm.calls[0]["tools"][0]["name"] == "issue_refund"


def test_permanent_error_goes_straight_to_dlq() -> None:
    api = main.FlakyPaymentsAPI()
    queue = main.InMemoryQueue(max_deliveries=3)
    queue.send(main.Job("job-2", "Refund order B-9 for 5.00 GBP."))
    llm = MockLLM([main.refund_agent_mock] * 4)
    main.run_worker(queue, lambda job: main.run_refund_agent(llm, api, job, sleep=no_sleep, rng=lambda: 0.0), log=lambda _: None)
    assert [(job.id, job.deliveries) for job, _ in queue.dead] == [("job-2", 1)]  # no pointless redeliveries
    assert api.refunds == []


def test_transient_job_failure_dead_letters_after_max_deliveries() -> None:
    queue = main.InMemoryQueue(max_deliveries=3)
    queue.send(main.Job("job-3", "anything"))

    def always_overloaded(_job: main.Job) -> str:
        raise main.APIError(529, "overloaded")

    main.run_worker(queue, always_overloaded, log=lambda _: None)
    assert [(job.id, job.deliveries) for job, _ in queue.dead] == [("job-3", 3)]


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    main.main()
    out = capsys.readouterr().out
    assert "refunds actually made: 2" in out and "refunds actually made: 1" in out
    assert "dead-letter queue: [('job-2'" in out
