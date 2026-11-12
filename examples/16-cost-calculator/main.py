"""Work out what an agent run costs, and see why cost grows faster than the number of steps.

    python main.py                         # from this folder
    python 16-cost-calculator/main.py      # from examples/

Anthropic prices are as of November 2026, from https://platform.claude.com/docs/en/about-claude/pricing
(US dollars per million tokens). Prices change: check the page before you rely on them.
OpenAI prices are deliberately not hard-coded. Set OPENAI_INPUT_PRICE and OPENAI_OUTPUT_PRICE
(dollars per million tokens, from https://platform.openai.com/docs/pricing) to include a model of yours.

Read alongside docs/16-cost-and-performance/16.1-token-cost-maths.md.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import Usage  # noqa: E402

MILLION = 1_000_000


@dataclass(frozen=True)
class Price:
    """Dollars per million tokens."""

    input: float
    output: float
    cache_write_5m: float | None = None  # writing to the 5-minute prompt cache
    cache_read: float | None = None  # reading from the prompt cache


# Claude prices, November 2026 (Haiku 5.5: prompts up to 100,000 tokens; longer prompts cost more).
PRICES: dict[str, Price] = {
    "claude-opus-5-5": Price(input=4.00, output=20.00, cache_write_5m=5.00, cache_read=0.20),
    "claude-sonnet-5-5": Price(input=2.00, output=10.00, cache_write_5m=2.50, cache_read=0.10),
    "claude-haiku-5-5": Price(input=0.10, output=0.50, cache_write_5m=0.125, cache_read=0.01),
}


def openai_price_from_env() -> Price | None:
    """An OpenAI model's price, if you set it yourself. We don't guess prices that change."""
    try:
        return Price(input=float(os.environ["OPENAI_INPUT_PRICE"]), output=float(os.environ["OPENAI_OUTPUT_PRICE"]))
    except (KeyError, ValueError):
        return None


def call_cost(price: Price, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float:
    """Dollar cost of one model call. `input_tokens` is the uncached part only (as Anthropic reports it)."""
    cost = input_tokens * price.input + output_tokens * price.output
    if cache_read:
        cost += cache_read * (price.cache_read if price.cache_read is not None else price.input)
    if cache_write:
        cost += cache_write * (price.cache_write_5m if price.cache_write_5m is not None else price.input)
    return cost / MILLION


def run_cost(price: Price, usages: list[Usage]) -> float:
    """Dollar cost of a whole run, from the usage of each model call (e.g. collected from your traces)."""
    return sum(call_cost(price, u.input_tokens, u.output_tokens) for u in usages)


# --------------------------------------------------------------------------- the agent-loop model


@dataclass(frozen=True)
class LoopShape:
    """The token budget of one typical step. All numbers are tokens."""

    fixed: int = 3_000  # system prompt + tool definitions, sent on every call
    goal: int = 100  # the user's request
    output: int = 200  # what the model writes per step (thinking, text and the tool call)
    tool_result: int = 800  # what each step's tool result adds to the conversation


def loop_usage(shape: LoopShape, steps: int) -> list[Usage]:
    """Usage per model call for an agent that runs `steps` calls, resending the whole conversation each time."""
    usages = []
    history = 0  # tokens added by earlier steps (model output + tool result)
    for _ in range(steps):
        usages.append(Usage(input_tokens=shape.fixed + shape.goal + history, output_tokens=shape.output))
        history += shape.output + shape.tool_result
    return usages


def loop_input_closed_form(shape: LoopShape, steps: int) -> int:
    """Total input tokens without a loop: n*(fixed+goal) + per_step * n(n-1)/2. The n² term is the resending."""
    per_step = shape.output + shape.tool_result
    return steps * (shape.fixed + shape.goal) + per_step * steps * (steps - 1) // 2


def main() -> None:
    opus = PRICES["claude-opus-5-5"]
    print("1) One call: 2,000 tokens in, 500 tokens out")
    for name, price in PRICES.items():
        print(f"   {name:<18} ${call_cost(price, 2_000, 500):.6f}")

    shape = LoopShape()
    print(f"\n2) An agent loop: {shape}")
    print("   steps   input tokens   output tokens   Opus 5.5   Sonnet 5.5   Haiku 5.5")
    for steps in (1, 5, 10, 20, 40):
        usages = loop_usage(shape, steps)
        tin = sum(u.input_tokens for u in usages)
        tout = sum(u.output_tokens for u in usages)
        costs = [run_cost(PRICES[m], usages) for m in PRICES]
        money = [f"${costs[0]:.3f}", f"${costs[1]:.3f}", f"${costs[2]:.4f}"]
        print(f"   {steps:>5} {tin:>14,} {tout:>15,}   {money[0]:>8}   {money[1]:>10}   {money[2]:>9}")

    ten, twenty = loop_usage(shape, 10), loop_usage(shape, 20)
    ratio = run_cost(opus, twenty) / run_cost(opus, ten)
    print(f"\n   Doubling the steps from 10 to 20 multiplies the Opus 5.5 cost by {ratio:.1f}x, not 2x.")

    print("\n3) Where the 10-step run's input tokens come from")
    tin = loop_input_closed_form(shape, 10)
    fixed = 10 * (shape.fixed + shape.goal)
    print(f"   fixed prefix resent 10 times: {fixed:>7,} ({fixed / tin:.0%})")
    print(f"   growing history resent:       {tin - fixed:>7,} ({(tin - fixed) / tin:.0%})")

    oa = openai_price_from_env()
    if oa:
        print(f"\n4) Your OpenAI model (prices from env): 10 steps = ${run_cost(oa, ten):.3f}")
    else:
        print("\n4) Set OPENAI_INPUT_PRICE and OPENAI_OUTPUT_PRICE to compare an OpenAI model.")


if __name__ == "__main__":
    main()
