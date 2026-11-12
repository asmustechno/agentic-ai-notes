"""An eval runner for regression testing an agent, offline on every PR and live on a schedule.

    python main.py                                   # replay recorded model replies (offline, free)
    python 12-regression-evals/main.py               # the same, from examples/
    python main.py --live --trials 3 --threshold 0.8 # call a real model (set LLM_PROVIDER and a key)
    python main.py --live --record                   # call a real model and save its replies as new recordings

Read alongside docs/12-evaluation/12.5-regression-testing-in-ci.md.

Exit code 0 means the pass rate met the threshold and nothing that passed in the
baseline now fails. Exit code 1 fails the CI job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

HERE = Path(__file__).resolve().parent
EVALS = HERE / "evals"

# --------------------------------------------------------------------------- the agent under test

ORDERS = {
    "1234": {"item": "Desk lamp", "total": 25.0, "status": "delivered"},
    "5678": {"item": "Headphones", "total": 60.0, "status": "shipped", "eta": "Thursday"},
    "9012": {"item": "Mug", "total": 12.0, "status": "processing"},
    "7777": {"item": "Chair", "total": 140.0, "status": "shipped", "eta": "Monday"},
    "3333": {"item": "TV", "total": 900.0, "status": "delivered"},
}

SYSTEM = (
    "You are a support agent for an online shop. Always look an order up with get_order before acting on it. "
    "You may refund up to the order total, and at most $500 without a human: for anything larger, call "
    "escalate_to_human instead of issue_refund. Only orders that are still processing can be cancelled. "
    "Answer in one or two sentences."
)


@dataclass
class Store:
    """The world the agent changes. Evals check this end state, not just the text."""

    refunds: dict[str, float] = field(default_factory=dict)
    cancelled: list[str] = field(default_factory=list)
    escalated: list[str] = field(default_factory=list)

    def state(self) -> dict[str, Any]:
        return {"refunds": self.refunds, "cancelled": self.cancelled, "escalated": self.escalated}


class ToolError(Exception):
    """A tool refused the request. The message goes back to the model with is_error=True."""


def get_order(store: Store, order_id: str) -> str:
    if order_id not in ORDERS:
        raise ToolError(f"No order {order_id}")
    return json.dumps({"order_id": order_id, **ORDERS[order_id]})


def issue_refund(store: Store, order_id: str, amount: float) -> str:
    order = ORDERS.get(order_id)
    if order is None or amount <= 0 or amount > order["total"]:
        raise ToolError(f"Refund of {amount} is not allowed for order {order_id}")
    store.refunds[order_id] = amount
    return f"Refunded ${amount:.2f} for order {order_id}"


def cancel_order(store: Store, order_id: str) -> str:
    order = ORDERS.get(order_id)
    if order is None or order["status"] != "processing":
        raise ToolError(f"Order {order_id} cannot be cancelled (status: {order and order['status']})")
    store.cancelled.append(order_id)
    return f"Order {order_id} cancelled"


def escalate_to_human(store: Store, order_id: str, reason: str) -> str:
    store.escalated.append(order_id)
    return f"Escalated order {order_id} to a human: {reason}"


TOOLS: dict[str, Callable[..., str]] = {
    "get_order": get_order,
    "issue_refund": issue_refund,
    "cancel_order": cancel_order,
    "escalate_to_human": escalate_to_human,
}


def _spec(name: str, description: str, **props: str) -> ToolSpec:
    types = {"amount": "number"}
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {p: {"type": types.get(p, "string"), "description": d} for p, d in props.items()},
            "required": list(props),
        },
    }


TOOL_SPECS: list[ToolSpec] = [
    _spec("get_order", "Look up an order: item, total, status and delivery estimate.", order_id="Order number"),
    _spec("issue_refund", "Refund part or all of an order, up to its total.", order_id="Order number",
          amount="Amount in USD"),
    _spec("cancel_order", "Cancel an order that is still processing.", order_id="Order number"),
    _spec("escalate_to_human", "Hand the case to a human agent.", order_id="Order number",
          reason="Why a human is needed"),
]


def run_agent(llm: LLM, question: str, store: Store, max_steps: int = 6) -> tuple[str, list[Message]]:
    """A plain agent loop (chapter 02). Returns the final answer and the full conversation."""
    messages: list[Message] = [user(question)]
    for _ in range(max_steps):
        reply = llm.chat(messages, system=SYSTEM, tools=TOOL_SPECS)
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text, messages
        for call in reply.tool_calls:
            try:
                messages.append(tool_result(call.id, TOOLS[call.name](store, **call.arguments)))
            except (ToolError, KeyError, TypeError) as exc:
                messages.append(tool_result(call.id, f"Error: {exc}", is_error=True))
    return "Sorry, I could not finish.", messages


# --------------------------------------------------------------------------- recordings ("cassettes")


class StaleRecording(RuntimeError):
    """The prompt or tools changed since the replies were recorded. Re-record them."""


def prompt_fingerprint() -> str:
    """A short hash of everything the model sees besides the conversation."""
    blob = SYSTEM + json.dumps(TOOL_SPECS, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _to_dict(resp: LLMResponse) -> dict[str, Any]:
    return {"text": resp.text, "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in resp.tool_calls]}


def _from_dict(d: dict[str, Any]) -> LLMResponse:
    if d["tool_calls"]:
        return MockLLM.tool_calls([(c["name"], c["arguments"]) for c in d["tool_calls"]], text=d["text"])
    return MockLLM.text(d["text"])


def replay_llm(case_id: str, recorded_dir: Path = EVALS / "recorded") -> MockLLM:
    """A MockLLM that returns exactly what the real model said when this case was recorded."""
    data = json.loads((recorded_dir / f"{case_id}.json").read_text(encoding="utf-8"))
    if data["prompt_fingerprint"] != prompt_fingerprint():
        raise StaleRecording(f"{case_id}: prompt or tools changed since recording; run with --live --record")
    return MockLLM([_from_dict(r) for r in data["replies"]])


class RecordingLLM(LLM):
    """Wraps a real model and keeps every reply, so a live run can become tomorrow's offline test."""

    def __init__(self, inner: LLM) -> None:
        self.inner, self.provider, self.model = inner, inner.provider, inner.model
        self.replies: list[dict[str, Any]] = []

    def chat(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        resp = self.inner.chat(messages, **kwargs)
        self.replies.append(_to_dict(resp))
        return resp

    def save(self, path: Path) -> None:
        payload = {"prompt_fingerprint": prompt_fingerprint(), "model": self.model, "replies": self.replies}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- grading and the suite


def load_cases(path: Path = EVALS / "cases.jsonl") -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def grade(case: dict[str, Any], answer: str, store: Store) -> list[str]:
    """Return the reasons a case failed. An empty list means it passed."""
    problems = []
    if store.state() != case["expected_state"]:
        problems.append(f"end state {store.state()} != expected {case['expected_state']}")
    problems += [f"answer is missing {word!r}" for word in case["must_contain"] if word.lower() not in answer.lower()]
    return problems


def run_case(case: dict[str, Any], llm: LLM) -> dict[str, Any]:
    store = Store()
    answer, messages = run_agent(llm, case["input"], store)
    problems = grade(case, answer, store)
    return {"id": case["id"], "tags": case["tags"], "passed": not problems, "problems": problems, "answer": answer}


def run_suite(cases: list[dict[str, Any]], make_llm: Callable[[dict[str, Any]], LLM], trials: int = 1) -> list[dict[str, Any]]:
    """Run every case `trials` times. `make_llm(case)` returns a fresh model for one run."""
    return [run_case(case, make_llm(case)) | {"trial": t} for case in cases for t in range(1, trials + 1)]


def regressions(results: list[dict[str, Any]], baseline: dict[str, bool]) -> list[str]:
    """Cases that passed in the baseline but have a failing trial now."""
    failing = {r["id"] for r in results if not r["passed"]}
    return sorted(cid for cid, passed in baseline.items() if passed and cid in failing)


def report(results: list[dict[str, Any]], threshold: float, baseline: dict[str, bool]) -> int:
    """Print a summary and return the exit code for CI."""
    for r in results:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['id']:<18} trial {r['trial']}  {'; '.join(r['problems'])}".rstrip())
    rate = sum(r["passed"] for r in results) / len(results)
    tags = sorted({t for r in results for t in r["tags"]})
    print("\nBy tag: " + ", ".join(
        f"{t} {sum(r['passed'] for r in results if t in r['tags'])}/{sum(t in r['tags'] for r in results)}" for t in tags))
    new_failures = regressions(results, baseline)
    print(f"Pass rate: {rate:.0%} (threshold {threshold:.0%})")
    print(f"Regressions vs baseline: {', '.join(new_failures) or 'none'}")
    ok = rate >= threshold and not new_failures
    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the model chosen by LLM_PROVIDER")
    parser.add_argument("--record", action="store_true", help="with --live: save replies to evals/recorded/")
    parser.add_argument("--trials", type=int, default=1, help="runs per case (use 3+ for live evals)")
    parser.add_argument("--threshold", type=float, default=0.8, help="minimum pass rate")
    parser.add_argument("--out", type=Path, help="write per-case results as JSON here")
    args = parser.parse_args(argv)

    cases = load_cases()
    baseline = json.loads((EVALS / "baseline.json").read_text(encoding="utf-8"))
    print(f"Running {len(cases)} cases x {args.trials if args.live else 1} trial(s), "
          f"{'live' if args.live else 'replaying recorded replies'} (prompt {prompt_fingerprint()})\n")
    if args.live:
        llm = get_llm()
        if llm.provider == "mock":
            parser.error("--live needs LLM_PROVIDER=anthropic or openai")

        def make_llm(case: dict[str, Any]) -> LLM:
            return RecordingLLM(llm) if args.record else llm

        results = []
        for case in cases:
            for t in range(1, args.trials + 1):
                model = make_llm(case)
                results.append(run_case(case, model) | {"trial": t})
                if args.record and t == 1:
                    model.save(EVALS / "recorded" / f"{case['id']}.json")
    else:
        results = run_suite(cases, lambda case: replay_llm(case["id"]))

    code = report(results, args.threshold, baseline)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
