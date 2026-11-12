"""Plan-and-execute: a planner writes the whole plan first, then an executor carries it out step by step.

    python main.py                        # from this folder
    python 07-plan-and-execute/main.py    # from examples/

1. PLAN     one model call returns a JSON plan: steps with ids, dependencies and "done when" criteria.
2. CHECK    our code validates the plan (unique ids, known dependencies, no cycles).
3. EXECUTE  steps run in dependency order. Each step is a small tool loop that must end with
            "DONE: ..." or "FAILED: ...". Steps in the same batch do not depend on each other.
4. ANSWER   one last call turns the step results into the final answer.

Read alongside docs/07-planning-and-reasoning/07.2-plan-and-execute.md and 07.3-task-decomposition.md.
What happens when a step fails is in examples/07-replanning.
"""

from __future__ import annotations

import ast
import json
import operator
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- tools (fake data)

VENUES = [
    {"id": "v1", "name": "Casa Azul", "city": "Lisbon", "capacity": 15, "day_rate_eur": 900},
    {"id": "v2", "name": "LX Loft", "city": "Lisbon", "capacity": 20, "day_rate_eur": 1100},
    {"id": "v3", "name": "Tejo Hall", "city": "Lisbon", "capacity": 40, "day_rate_eur": 2000},
]
BOOKED = {("v1", "2026-12-04")}  # Casa Azul is taken on 4 December (see 07-replanning)


def search_venues(city: str, min_capacity: int) -> str:
    found = [v for v in VENUES if v["city"].lower() == city.lower() and v["capacity"] >= min_capacity]
    return json.dumps(found)


def check_availability(venue_id: str, date: str) -> str:
    if venue_id not in {v["id"] for v in VENUES}:
        return f"Error: unknown venue {venue_id}"
    return json.dumps({"venue_id": venue_id, "date": date, "available": (venue_id, date) not in BOOKED})


_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
}


def calculator(expression: str) -> str:
    """Safe arithmetic: numbers and + - * / only."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("only numbers and + - * / are allowed")

    try:
        result = ev(ast.parse(expression, mode="eval").body)
        return str(int(result)) if float(result).is_integer() else str(result)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"Error: {exc}"


def _schema(props: dict[str, str]) -> dict:
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}, "required": list(props)}


TOOLS: dict[str, tuple[Callable[..., str], ToolSpec]] = {
    "search_venues": (search_venues, {
        "name": "search_venues",
        "description": "List venues in a city that hold at least min_capacity people, with their day rate in EUR.",
        "input_schema": _schema({"city": "string", "min_capacity": "integer"}),
    }),
    "check_availability": (check_availability, {
        "name": "check_availability",
        "description": "Check whether a venue (by id, e.g. 'v1') is free on a date (YYYY-MM-DD).",
        "input_schema": _schema({"venue_id": "string", "date": "string"}),
    }),
    "calculator": (calculator, {
        "name": "calculator",
        "description": "Evaluate arithmetic with + - * / and numbers, e.g. '12 * 25'.",
        "input_schema": _schema({"expression": "string"}),
    }),
}

# --------------------------------------------------------------------------- the plan


@dataclass
class Step:
    id: str
    task: str
    depends_on: list[str] = field(default_factory=list)
    done_when: str = ""
    status: str = "pending"  # pending | done | failed
    result: str = ""


class PlanError(ValueError):
    """The planner returned something we cannot run."""


def parse_plan(text: str) -> list[Step]:
    """Turn the planner's JSON into Steps, and reject plans we cannot execute."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())  # tolerate a fenced code block
    try:
        raw = json.loads(text)["steps"]
        steps = [Step(id=s["id"], task=s["task"], depends_on=list(s.get("depends_on", [])),
                      done_when=s.get("done_when", "")) for s in raw]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PlanError(f"Plan is not valid JSON in the expected shape: {exc}") from exc
    ids = [s.id for s in steps]
    if not steps or len(ids) != len(set(ids)):
        raise PlanError("Plan must have at least one step and unique step ids.")
    for s in steps:
        unknown = set(s.depends_on) - set(ids)
        if unknown:
            raise PlanError(f"Step {s.id} depends on unknown steps {sorted(unknown)}.")
    try:
        batches(steps)
    except CycleError as exc:
        raise PlanError(f"Plan has a dependency cycle: {exc.args[1]}") from exc
    return steps


def batches(steps: list[Step]) -> list[list[str]]:
    """Group step ids into batches: every step's dependencies are in earlier batches.
    Steps in the same batch are independent, so they could run in parallel."""
    sorter = TopologicalSorter({s.id: s.depends_on for s in steps})
    sorter.prepare()
    out: list[list[str]] = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        out.append(ready)
        sorter.done(*ready)
    return out


# --------------------------------------------------------------------------- planner, executor, answerer

PLANNER_SYSTEM = """You are a planner. Break the user's goal into 2-6 small steps that an assistant with these
tools can carry out: search_venues, check_availability, calculator.

Reply with JSON only, in this shape:
{"steps": [{"id": "s1", "task": "...", "depends_on": [], "done_when": "..."}]}

- Each task does one thing. "done_when" says how to tell the step is finished.
- depends_on lists the ids of steps whose results this step needs. Leave it empty if none.
- Do not do the work yourself. Only plan."""

EXECUTOR_SYSTEM = """You carry out ONE step of a larger plan, using tools. Results of earlier steps are given to you.
When the step is finished, reply with text that starts with "DONE:" followed by the result in one or two sentences.
If you cannot meet the step's done-when criterion, reply "FAILED:" followed by the reason. Do not do other steps."""

ANSWER_SYSTEM = "Write the final answer to the user's goal from the step results. Be brief and give the key numbers."


@dataclass
class PlanAndExecute:
    llm: LLM
    max_tool_turns: int = 4  # per step
    log: list[str] = field(default_factory=list)

    def plan(self, goal: str) -> list[Step]:
        reply = self.llm.chat([user(goal)], system=PLANNER_SYSTEM)
        steps = parse_plan(reply.text)
        for s in steps:
            after = f" (after {', '.join(s.depends_on)})" if s.depends_on else ""
            self.log.append(f"plan  {s.id}: {s.task}{after}")
        self.log.append(f"order {' -> '.join('[' + ', '.join(b) + ']' for b in batches(steps))}")
        return steps

    def execute_step(self, goal: str, step: Step, done: dict[str, Step]) -> None:
        context = "\n".join(f"- {d}: {done[d].result}" for d in step.depends_on) or "(none)"
        messages: list[Message] = [user(
            f"Overall goal: {goal}\n\nYour step ({step.id}): {step.task}\nDone when: {step.done_when}\n\n"
            f"Results of earlier steps:\n{context}"
        )]
        specs = [spec for _, spec in TOOLS.values()]
        for _ in range(self.max_tool_turns):
            reply = self.llm.chat(messages, system=EXECUTOR_SYSTEM, tools=specs)
            messages.append(reply.to_message())
            if not reply.tool_calls:
                text = reply.text.strip()
                step.status = "done" if text.upper().startswith("DONE") else "failed"
                step.result = re.sub(r"^(DONE|FAILED):\s*", "", text, flags=re.I)
                self.log.append(f"{step.status:5} {step.id}: {step.result}")
                return
            for call in reply.tool_calls:
                fn, _ = TOOLS.get(call.name, (None, None))
                result = fn(**call.arguments) if fn else f"Error: unknown tool {call.name}"
                shown = result if len(result) <= 80 else result[:77] + "..."
                self.log.append(f"  tool {call.name}({call.arguments}) -> {shown}")
                messages.append(tool_result(call.id, result, is_error=result.startswith("Error")))
        step.status, step.result = "failed", f"no result after {self.max_tool_turns} tool turns"
        self.log.append(f"failed {step.id}: {step.result}")

    def run(self, goal: str) -> str:
        steps = self.plan(goal)
        by_id = {s.id: s for s in steps}
        for batch in batches(steps):
            for step_id in batch:  # independent steps; a real system could run these concurrently
                self.execute_step(goal, by_id[step_id], by_id)
                if by_id[step_id].status == "failed":
                    return f"Stopped: step {step_id} failed ({by_id[step_id].result}). See 07-replanning."
        results = "\n".join(f"- {s.id} ({s.task}): {s.result}" for s in steps)
        reply = self.llm.chat([user(f"Goal: {goal}\n\nStep results:\n{results}")], system=ANSWER_SYSTEM)
        return reply.text


# --------------------------------------------------------------------------- demo script

GOAL = ("Find a venue in Lisbon for our 12-person offsite on 2026-12-03. Total budget is EUR 1,500, "
        "including lunch at EUR 25 per person. Which venue should we pick, and what is the total cost?")

PLAN_JSON = json.dumps({"steps": [
    {"id": "s1", "task": "Find Lisbon venues that hold at least 12 people", "depends_on": [],
     "done_when": "we have a list of venues with day rates"},
    {"id": "s2", "task": "Check the cheapest venue is free on 2026-12-03", "depends_on": ["s1"],
     "done_when": "one available venue and its day rate are known"},
    {"id": "s3", "task": "Work out lunch for 12 people at EUR 25 each", "depends_on": [],
     "done_when": "the lunch total in EUR is known"},
    {"id": "s4", "task": "Add venue rate and lunch, and compare with the EUR 1,500 budget", "depends_on": ["s2", "s3"],
     "done_when": "the total is known and we know if it is within budget"},
]}, indent=1)

SCRIPT = [
    PLAN_JSON,
    # batch 1: s1 and s3 (independent)
    MockLLM.tool_call("search_venues", {"city": "Lisbon", "min_capacity": 12}),
    "DONE: Casa Azul (v1, EUR 900/day), LX Loft (v2, EUR 1,100/day) and Tejo Hall (v3, EUR 2,000/day) hold 12+.",
    MockLLM.tool_call("calculator", {"expression": "12 * 25"}),
    "DONE: Lunch costs EUR 300.",
    # batch 2: s2
    MockLLM.tool_call("check_availability", {"venue_id": "v1", "date": "2026-12-03"}),
    "DONE: Casa Azul (v1) is available on 2026-12-03 at EUR 900.",
    # batch 3: s4
    MockLLM.tool_call("calculator", {"expression": "900 + 300"}),
    "DONE: Total is EUR 1,200, which is EUR 300 under the EUR 1,500 budget.",
    # final answer
    "Book Casa Azul on 3 December: EUR 900 for the venue plus EUR 300 for lunch makes EUR 1,200, "
    "EUR 300 under budget.",
]


def main() -> None:
    agent = PlanAndExecute(get_llm(mock_responses=SCRIPT))
    print(f"Goal: {GOAL}\n")
    answer = agent.run(GOAL)
    print("\n".join(agent.log))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
