"""Cap steps, tokens, dollars and seconds for every agent run, and stop gracefully when a cap is reached.

    python main.py                       # from this folder
    python 16-budget-limits/main.py      # from examples/

Two kinds of limit work together:

    a signal  the model can see ("this is your last step, answer now"), so it can finish well
    a stop    your code enforces, so the run ends even if the model ignores the signal

Read alongside docs/16-cost-and-performance/16.5-budget-limits-per-run.md.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, Usage, get_llm, tool_result, user  # noqa: E402

PRICE_IN, PRICE_OUT = 4.00, 20.00  # Claude Opus 5.5, $ per million tokens (Nov 2026)
LAST_STEP_NOTE = "Budget note: this is your final step. Do not call tools. Give your best answer now with what you have."


@dataclass(frozen=True)
class Budget:
    """Per-run caps. None means no cap of that kind."""

    max_steps: int | None = 10
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_dollars: float | None = None
    max_seconds: float | None = None


@dataclass
class BudgetTracker:
    """Counts what a run has used and decides whether the next model call may go ahead."""

    budget: Budget
    price_in: float = PRICE_IN
    price_out: float = PRICE_OUT
    clock: Callable[[], float] = time.monotonic
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started: float | None = None
    last_input: int = 0

    def start(self) -> None:
        self.started = self.clock()

    @property
    def dollars(self) -> float:
        return (self.input_tokens * self.price_in + self.output_tokens * self.price_out) / 1e6

    @property
    def seconds(self) -> float:
        return 0.0 if self.started is None else self.clock() - self.started

    def record(self, usage: Usage) -> None:
        self.steps += 1
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.last_input = usage.input_tokens

    def stop_reason(self, next_input_estimate: int = 0) -> str | None:
        """Why the next call must not happen, or None. Checks *before* spending, using an estimate."""
        b = self.budget
        if b.max_steps is not None and self.steps >= b.max_steps:
            return f"step limit ({b.max_steps})"
        if b.max_seconds is not None and self.seconds >= b.max_seconds:
            return f"time limit ({b.max_seconds:g}s)"
        if b.max_input_tokens is not None and self.input_tokens + next_input_estimate > b.max_input_tokens:
            return f"input-token limit ({b.max_input_tokens:,})"
        if b.max_output_tokens is not None and self.output_tokens >= b.max_output_tokens:
            return f"output-token limit ({b.max_output_tokens:,})"
        if b.max_dollars is not None:
            next_cost = next_input_estimate * self.price_in / 1e6
            if self.dollars + next_cost > b.max_dollars:
                return f"dollar limit (${b.max_dollars:g})"
        return None

    def is_last_step(self) -> bool:
        """True when the next call is the last one the step cap allows: time to tell the model."""
        return self.budget.max_steps is not None and self.steps == self.budget.max_steps - 1

    def summary(self) -> dict[str, float | int]:
        return {"steps": self.steps, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "dollars": round(self.dollars, 6), "seconds": round(self.seconds, 2)}


@dataclass
class RunResult:
    answer: str
    stopped_by: str | None  # None means the model finished on its own
    usage: dict[str, float | int]
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- a research agent with a budget

PAGES = {f"p{i}": f"Page {i}: " + "notes about heat pumps. " * 40 for i in range(1, 9)}


def search(query: str) -> str:
    """Fake web search: always returns another long page, so the context keeps growing."""
    page = f"p{len(query) % 8 + 1}"
    return json.dumps({"page": page, "text": PAGES[page]})


SEARCH_SPEC: ToolSpec = {
    "name": "search",
    "description": "Search the web and return the text of the best page.",
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}


def researcher(messages: list[Message]) -> LLMResponse | str:
    """A scripted model that keeps researching until it has 6 results, but obeys the budget note."""
    last = messages[-1]
    if last["role"] == "user" and LAST_STEP_NOTE in str(last["content"]):
        n = sum(1 for m in messages if m["role"] == "tool")
        return f"From the {n} sources I read: heat pumps cut heating bills in most climates. (Partial answer.)"
    n = sum(1 for m in messages if m["role"] == "tool")
    if n < 6:
        return MockLLM.tool_call("search", {"query": f"heat pump running costs, angle {n + 1}"})
    return "From 6 sources: heat pumps cut heating bills in most climates, by roughly a third for typical homes."


GOAL = "Do heat pumps save money? Research it and summarise."


@dataclass
class BudgetedAgent:
    llm: LLM
    budget: Budget
    clock: Callable[[], float] = time.monotonic
    tools: dict[str, tuple[Callable[..., str], ToolSpec]] = field(default_factory=lambda: {"search": (search, SEARCH_SPEC)})

    def run(self, goal: str) -> RunResult:
        tracker = BudgetTracker(self.budget, clock=self.clock)
        tracker.start()
        messages: list[Message] = [user(goal)]
        specs = [s for _, s in self.tools.values()]
        notes: list[str] = []
        last_text = ""
        growth = 0  # how much the input grew last step; used to estimate the next call
        while True:
            estimate = tracker.last_input + growth if tracker.steps else 0
            reason = tracker.stop_reason(next_input_estimate=estimate)
            if reason:  # STOP: enforced by code, before spending more
                return RunResult(self._graceful(last_text, reason), reason, tracker.summary(), notes)
            if tracker.is_last_step():  # SIGNAL: tell the model, so it can finish well
                messages.append(user(LAST_STEP_NOTE))
                notes.append(f"step {tracker.steps + 1}: told the model it is the last step")
            before = tracker.last_input
            reply = self.llm.chat(messages, system="You are a careful research assistant.", tools=specs)
            tracker.record(reply.usage)
            growth = max(0, tracker.last_input - before) if before else 0
            messages.append(reply.to_message())
            last_text = reply.text or last_text
            if not reply.tool_calls:
                return RunResult(reply.text, None, tracker.summary(), notes)
            for call in reply.tool_calls:
                messages.append(tool_result(call.id, self.tools[call.name][0](**call.arguments)))

    @staticmethod
    def _graceful(last_text: str, reason: str) -> str:
        """Never end with a stack trace: say what happened and hand back what there is."""
        partial = f" The last thing I wrote was: {last_text!r}" if last_text else ""
        return f"I stopped before finishing because this run hit its {reason}.{partial}"


def main() -> None:
    runs = {
        "no tight limits": Budget(max_steps=20),
        "max_steps=4": Budget(max_steps=4),
        "max_dollars=$0.004": Budget(max_steps=20, max_dollars=0.004),
    }
    for label, budget in runs.items():
        agent = BudgetedAgent(llm=get_llm(mock_responses=[researcher] * 20), budget=budget)
        result = agent.run(GOAL)
        print(f"{label}:")
        for note in result.notes:
            print(f"  note:   {note}")
        print(f"  stopped by: {result.stopped_by or 'model finished'}")
        print(f"  usage:  {result.usage}")
        print(f"  answer: {result.answer}\n")


if __name__ == "__main__":
    main()
