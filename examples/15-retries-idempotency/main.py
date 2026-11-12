"""Retry safely: backoff with jitter, which errors to retry, idempotency keys and a dead-letter queue.

    python main.py                              # from this folder
    python 15-retries-idempotency/main.py       # from examples/

Read alongside docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md.

Everything here is in-memory and deterministic (a seeded random generator and a
fake `sleep`), so the run is the same every time. Real systems use a real queue
(SQS, RabbitMQ, Redis streams, Pub/Sub...) and a real payments API, but the
rules are the same.
"""

from __future__ import annotations

import random
import re
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

T = TypeVar("T")

# --------------------------------------------------------------------------- 1. which errors to retry


class APIError(Exception):
    """An HTTP error from some API, with the status code and an optional Retry-After (seconds)."""

    def __init__(self, status_code: int, message: str = "", retry_after: float | None = None) -> None:
        super().__init__(f"{status_code} {message}".strip())
        self.status_code = status_code
        self.retry_after = retry_after


# Worth retrying: the same request may succeed later.
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


def is_retryable(exc: BaseException) -> bool:
    """True for timeouts, dropped connections, rate limits and server errors. False for everything else.

    A 400 (bad request), 401 (bad key), 403 (forbidden) or 404 (not found) will fail
    the same way every time, so retrying only wastes time and money.
    """
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)
    return status is not None and (status in RETRYABLE_STATUS or status >= 500)


# --------------------------------------------------------------------------- 2. exponential backoff with jitter


def backoff_delay(attempt: int, *, base: float = 0.5, cap: float = 30.0, rng: Callable[[], float] = random.random) -> float:
    """'Full jitter': a random wait between 0 and min(cap, base * 2**attempt) seconds.

    Exponential growth gives a struggling service room to recover; the randomness
    stops a crowd of clients that failed together from retrying together.
    """
    return rng() * min(cap, base * 2**attempt)


def retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    base: float = 0.5,
    cap: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    log: Callable[[str], None] = print,
) -> T:
    """Call `fn` until it succeeds, retrying only retryable errors, with backoff between attempts."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts - 1:
                raise
            # If the server said how long to wait (Retry-After), do what it says.
            delay = getattr(exc, "retry_after", None) or backoff_delay(attempt, base=base, cap=cap, rng=rng)
            log(f"    attempt {attempt + 1} failed ({type(exc).__name__}: {exc}); retrying in {delay:.2f}s")
            sleep(delay)
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- 3. idempotency keys


class FlakyPaymentsAPI:
    """A fake refunds API whose network sometimes loses the *response* after the refund was made.

    That is the dangerous case: the caller sees a timeout, but the money has moved.
    Like Stripe's API, it accepts an optional idempotency key: a request that
    repeats a key already seen returns the first result instead of refunding again.
    """

    def __init__(self, lose_responses: int = 0) -> None:
        self.lose_responses = lose_responses
        self.refunds: list[dict[str, Any]] = []  # what really happened, for the demo and the tests
        self._by_key: dict[str, dict[str, Any]] = {}

    def refund(self, order_id: str, amount: float, *, idempotency_key: str | None = None) -> dict[str, Any]:
        if not re.fullmatch(r"A-\d{4}", order_id):
            raise APIError(400, f"invalid order id {order_id!r}")  # permanent: never retry
        if idempotency_key and idempotency_key in self._by_key:
            result = self._by_key[idempotency_key]  # replay: same answer, no second refund
        else:
            result = {"refund_id": f"re_{len(self.refunds) + 1}", "order_id": order_id, "amount": amount}
            self.refunds.append(result)
            if idempotency_key:
                self._by_key[idempotency_key] = result
        if self.lose_responses > 0:
            self.lose_responses -= 1
            raise TimeoutError("response lost on the way back")
        return result


def refund_with_retries(
    api: FlakyPaymentsAPI, order_id: str, amount: float, *, key: str | None, sleep: Callable[[float], None], rng: Callable[[], float]
) -> dict[str, Any]:
    """Issue a refund, retrying transient failures. Every retry reuses the SAME key."""
    return retry(lambda: api.refund(order_id, amount, idempotency_key=key), sleep=sleep, rng=rng)


# --------------------------------------------------------------------------- 4. an at-least-once queue with a DLQ


@dataclass
class Job:
    id: str
    goal: str
    deliveries: int = 0


@dataclass
class InMemoryQueue:
    """At-least-once delivery: a job stays in the queue until a worker acks it.

    If the worker fails or crashes first, the job is delivered again. After
    `max_deliveries` attempts, or at once for a permanent error, it moves to the
    dead-letter queue (DLQ) for a human to look at.
    """

    max_deliveries: int = 3
    ready: deque[Job] = field(default_factory=deque)
    dead: list[tuple[Job, str]] = field(default_factory=list)
    done: list[Job] = field(default_factory=list)

    def send(self, job: Job) -> None:
        self.ready.append(job)

    def receive(self) -> Job | None:
        if not self.ready:
            return None
        job = self.ready.popleft()
        job.deliveries += 1
        return job

    def ack(self, job: Job) -> None:
        self.done.append(job)

    def nack(self, job: Job, reason: str, *, retryable: bool) -> str:
        if retryable and job.deliveries < self.max_deliveries:
            self.ready.append(job)
            return "requeued"
        self.dead.append((job, reason))
        return "dead-lettered"


class WorkerCrash(Exception):
    """Stands in for the process dying (deploy, OOM kill) before it could ack."""


# --------------------------------------------------------------------------- 5. an agent whose tool is safe to repeat

REFUND_SPEC: ToolSpec = {
    "name": "issue_refund",
    "description": "Refund money to the customer for one order. Has a real side effect: money moves.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order id like 'A-1001'."},
            "amount": {"type": "number", "description": "Amount to refund, in GBP."},
        },
        "required": ["order_id", "amount"],
    },
}
SYSTEM = "You are a refunds agent. Use issue_refund exactly once for the order in the request, then confirm briefly."


def refund_agent_mock(messages: list[Message]) -> LLMResponse | str:
    """A scripted model for offline runs: asks for the refund, then confirms using the tool result."""
    results = [m for m in messages if m["role"] == "tool"]
    if not results:
        order = re.search(r"order (\S+)", messages[0]["content"])
        amount = re.search(r"(\d+(?:\.\d+)?) GBP", messages[0]["content"])
        return MockLLM.tool_call(
            "issue_refund", {"order_id": order.group(1) if order else "?", "amount": float(amount.group(1)) if amount else 0.0}
        )
    return f"Done. Tool said: {results[-1]['content']}"


def run_refund_agent(
    llm: LLM, api: FlakyPaymentsAPI, job: Job, *, sleep: Callable[[float], None], rng: Callable[[], float], max_steps: int = 4
) -> str:
    """A minimal agent loop. The tool derives its idempotency key from the JOB id, which survives redelivery."""
    messages: list[Message] = [user(job.goal)]
    for _ in range(max_steps):
        reply = llm.chat(messages, system=SYSTEM, tools=[REFUND_SPEC])
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text
        for call in reply.tool_calls:
            args = call.arguments
            # Not the tool_call id: a redelivered job calls the model again and gets a NEW id.
            key = f"{job.id}:refund:{args['order_id']}"
            try:
                out = refund_with_retries(api, args["order_id"], args["amount"], key=key, sleep=sleep, rng=rng)
                messages.append(tool_result(call.id, str(out)))
            except APIError as exc:
                if not is_retryable(exc):
                    raise  # a permanent error: let the worker dead-letter the job
                messages.append(tool_result(call.id, f"Error: {exc}", is_error=True))
    return "Stopped: step limit reached."


def run_worker(
    queue: InMemoryQueue,
    handle: Callable[[Job], str],
    *,
    crash_once_after: set[str] | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """Pull jobs until the queue is empty. Ack on success; nack (retry or DLQ) on failure."""
    crash_once_after = set(crash_once_after or ())
    while (job := queue.receive()) is not None:
        log(f"  deliver {job.id} (delivery {job.deliveries})")
        try:
            answer = handle(job)
            if job.id in crash_once_after:
                crash_once_after.discard(job.id)
                raise WorkerCrash("worker died after the work, before the ack")
            queue.ack(job)
            log(f"  ack     {job.id}: {answer}")
        except Exception as exc:
            retryable = isinstance(exc, WorkerCrash) or is_retryable(exc)
            outcome = queue.nack(job, f"{type(exc).__name__}: {exc}", retryable=retryable)
            log(f"  nack    {job.id}: {type(exc).__name__}: {exc} -> {outcome}")


# --------------------------------------------------------------------------- demo


def main() -> None:
    rng = random.Random(7).random  # seeded, so the "random" jitter is the same every run
    waits: list[float] = []

    def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    print("1) Backoff schedule, base 0.5s, cap 30s")
    print("   no jitter:   " + "  ".join(f"{min(30.0, 0.5 * 2**a):5.2f}" for a in range(6)))
    print("   full jitter: " + "  ".join(f"{backoff_delay(a, rng=rng):5.2f}" for a in range(6)))

    print("\n2) Refund through a network that loses the first response")
    for label, key in [("no idempotency key", None), ("with idempotency key", "order-A-1001-refund-1")]:
        api = FlakyPaymentsAPI(lose_responses=1)
        print(f"  {label}:")
        refund_with_retries(api, "A-1001", 20.0, key=key, sleep=fake_sleep, rng=rng)
        print(f"    refunds actually made: {len(api.refunds)}")

    print("\n3) A queue of agent jobs: one worker crash, one bad order")
    api = FlakyPaymentsAPI()
    queue = InMemoryQueue(max_deliveries=3)
    queue.send(Job("job-1", "Refund order A-1001 for 20.00 GBP. Reason: arrived damaged."))
    queue.send(Job("job-2", "Refund order B-9 for 5.00 GBP."))
    llm = get_llm(mock_responses=[refund_agent_mock] * 10)
    run_worker(
        queue,
        lambda job: run_refund_agent(llm, api, job, sleep=fake_sleep, rng=rng),
        crash_once_after={"job-1"},
    )
    print(f"\n  refunds actually made: {len(api.refunds)}  (job-1 ran twice, refunded once)")
    print(f"  dead-letter queue: {[(job.id, reason) for job, reason in queue.dead]}")


if __name__ == "__main__":
    main()
