"""Score recorded agent runs: final state, answer, trajectory, tool calls, cost, and pass@k vs pass^k.

    python main.py                              # from this folder
    python 12-trajectory-metrics/main.py        # from examples/

Read alongside docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md.

The runs in recorded_runs.jsonl were saved from a customer-support agent: three
tasks, four trials each. Recording runs once and scoring them offline is how
most eval pipelines work: running the agent is slow and costs money, scoring
is cheap and can be repeated whenever you change a metric.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from collections.abc import Iterable
from math import comb
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import Message  # noqa: E402

HERE = Path(__file__).resolve().parent
Call = dict[str, Any]  # {"name": "get_order", "arguments": {"order_id": "1234"}}

# Example prices in USD per million tokens (claude-opus-5-5, November 2026).
# Check https://platform.claude.com/docs/en/about-claude/pricing before relying on them.
PRICE_PER_MTOK = {"input": 4.00, "output": 20.00}


# --------------------------------------------------------------------------- loading


def load_tasks(path: Path = HERE / "tasks.json") -> dict[str, dict[str, Any]]:
    """Tasks keyed by id. Each has the expected tool calls, end state and answer keywords."""
    return {t["task_id"]: t for t in json.loads(path.read_text(encoding="utf-8"))}


def load_runs(path: Path = HERE / "recorded_runs.jsonl") -> list[dict[str, Any]]:
    """One JSON object per line: what the agent did in one trial of one task."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def trajectory_from_messages(messages: list[Message]) -> list[Call]:
    """Extract the tool calls, in order, from a conversation built with the shared wrapper.

    This is how you record a trajectory from your own agent: keep the messages list
    and pull out every assistant tool call.
    """
    return [
        {"name": tc.name, "arguments": tc.arguments}
        for m in messages
        if m["role"] == "assistant"
        for tc in m.get("tool_calls", [])
    ]


# --------------------------------------------------------------------------- outcome metrics


def final_state_ok(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    """The most important check: did the world end up the way it should?"""
    return actual == expected


def exact_match(answer: str, expected: str) -> bool:
    """Strict string equality after trimming and lower-casing. Only useful for short, closed answers."""
    return answer.strip().lower() == expected.strip().lower()


def keyword_score(answer: str, keywords: Iterable[str]) -> float:
    """Partial match: the fraction of required keywords that appear in the answer."""
    keywords = list(keywords)
    if not keywords:
        return 1.0
    return sum(k.lower() in answer.lower() for k in keywords) / len(keywords)


# --------------------------------------------------------------------------- trajectory metrics


def _key(call: Call, with_args: bool = True) -> str:
    """A hashable, order-independent fingerprint of a tool call."""
    return call["name"] + (json.dumps(call["arguments"], sort_keys=True) if with_args else "")


def strict_match(actual: list[Call], expected: list[Call], with_args: bool = True) -> bool:
    """Same calls, same order, nothing extra."""
    return [_key(c, with_args) for c in actual] == [_key(c, with_args) for c in expected]


def in_order_match(actual: list[Call], expected: list[Call], with_args: bool = True) -> bool:
    """Every expected call appears, in the expected order. Extra calls in between are allowed."""
    remaining = iter(_key(c, with_args) for c in actual)
    return all(any(a == e for a in remaining) for e in (_key(c, with_args) for c in expected))


def any_order_match(actual: list[Call], expected: list[Call], with_args: bool = True) -> bool:
    """Every expected call appears, in any order. Extra calls are allowed."""
    missing = Counter(_key(c, with_args) for c in expected) - Counter(_key(c, with_args) for c in actual)
    return not missing


def tool_precision_recall(actual: list[Call], expected: list[Call], with_args: bool = True) -> tuple[float, float]:
    """Precision: share of calls made that were expected. Recall: share of expected calls that were made."""
    a = Counter(_key(c, with_args) for c in actual)
    e = Counter(_key(c, with_args) for c in expected)
    hits = sum((a & e).values())
    precision = hits / sum(a.values()) if a else (1.0 if not e else 0.0)
    recall = hits / sum(e.values()) if e else 1.0
    return precision, recall


# --------------------------------------------------------------------------- reliability metrics


def pass_at_k(n: int, c: int, k: int) -> float:
    """Chance that AT LEAST ONE of k trials succeeds, estimated from c successes in n trials.

    Unbiased estimator from Chen et al. (2021): 1 - C(n-c, k) / C(n, k).
    """
    if k > n:
        raise ValueError("k cannot be larger than the number of trials n")
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k: chance that ALL k trials succeed, estimated from c successes in n trials.

    Estimator from the tau-bench paper (Yao et al., 2024): C(c, k) / C(n, k).
    """
    if k > n:
        raise ValueError("k cannot be larger than the number of trials n")
    return comb(c, k) / comb(n, k)


def cost_usd(input_tokens: int, output_tokens: int, prices: dict[str, float] = PRICE_PER_MTOK) -> float:
    """Cost of one run from its token counts."""
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


# --------------------------------------------------------------------------- putting it together


def score_run(run: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Every metric for one run. `success` is the headline: right end state AND all keywords present."""
    expected = task["expected_tool_calls"]
    actual = run["tool_calls"]
    precision, recall = tool_precision_recall(actual, expected)
    state_ok = final_state_ok(run["final_state"], task["expected_state"])
    keywords = keyword_score(run["answer"], task["answer_must_contain"])
    return {
        "task_id": run["task_id"],
        "trial": run["trial"],
        "success": state_ok and keywords == 1.0,
        "state_ok": state_ok,
        "keywords": keywords,
        "strict": strict_match(actual, expected),
        "in_order": in_order_match(actual, expected),
        "any_order": any_order_match(actual, expected),
        "precision": precision,
        "recall": recall,
        "steps": len(actual),
        "cost": cost_usd(run["input_tokens"], run["output_tokens"]),
        "latency_s": run["latency_s"],
    }


def reliability(scores: list[dict[str, Any]], ks: Iterable[int]) -> dict[int, tuple[float, float]]:
    """pass@k and pass^k for each k, averaged over tasks (each task weighs the same)."""
    by_task: dict[str, list[bool]] = {}
    for s in scores:
        by_task.setdefault(s["task_id"], []).append(s["success"])
    out = {}
    for k in ks:
        at_k = [pass_at_k(len(r), sum(r), k) for r in by_task.values()]
        hat_k = [pass_hat_k(len(r), sum(r), k) for r in by_task.values()]
        out[k] = (statistics.mean(at_k), statistics.mean(hat_k))
    return out


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def main() -> None:
    tasks = load_tasks()
    scores = [score_run(run, tasks[run["task_id"]]) for run in load_runs()]

    print(f"{'task':<15}{'#':>2}  {'success':<8}{'strict':<7}{'in-order':<9}{'any-order':<10}"
          f"{'prec':>5}{'rec':>6}{'steps':>6}{'cost $':>8}")
    for s in scores:
        print(f"{s['task_id']:<15}{s['trial']:>2}  {_yn(s['success']):<8}{_yn(s['strict']):<7}"
              f"{_yn(s['in_order']):<9}{_yn(s['any_order']):<10}{s['precision']:>5.2f}{s['recall']:>6.2f}"
              f"{s['steps']:>6}{s['cost']:>8.4f}")

    n = len(scores)
    print(f"\nTask success rate:     {sum(s['success'] for s in scores)}/{n} = "
          f"{sum(s['success'] for s in scores) / n:.0%}")
    print(f"Strict trajectory:     {sum(s['strict'] for s in scores)}/{n}")
    print(f"In-order trajectory:   {sum(s['in_order'] for s in scores)}/{n}")
    print(f"Mean tool precision:   {statistics.mean(s['precision'] for s in scores):.2f}")
    print(f"Mean tool recall:      {statistics.mean(s['recall'] for s in scores):.2f}")
    print(f"Mean steps per run:    {statistics.mean(s['steps'] for s in scores):.2f}")
    print(f"Mean cost per run:     ${statistics.mean(s['cost'] for s in scores):.4f}")
    latencies = sorted(s["latency_s"] for s in scores)
    print(f"Latency median / max:  {statistics.median(latencies):.1f}s / {latencies[-1]:.1f}s")

    print("\nReliability over 4 trials per task (averaged over tasks):")
    print("  k   pass@k   pass^k")
    for k, (at_k, hat_k) in reliability(scores, ks=range(1, 5)).items():
        print(f"  {k}   {at_k:6.2f}   {hat_k:6.2f}")


if __name__ == "__main__":
    main()
