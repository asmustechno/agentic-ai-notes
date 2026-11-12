"""Re-planning: when a step fails, keep what worked, ask the planner for a new plan for the rest, and know when to stop.

    python main.py                    # from this folder
    python 07-replanning/main.py      # from examples/

Same offsite task as 07-plan-and-execute, but on 4 December, when the cheapest venue is
already booked. The run:

  PLAN -> EXECUTE ... step s2 FAILED -> RE-PLAN (remaining work only) -> EXECUTE -> ANSWER

Limits that keep re-planning safe:
  * max_replans: after this many new plans, give up and report honestly;
  * the same step failing for the same reason twice also stops the run;
  * the planner may answer {"give_up": "..."} when the goal cannot be reached.

Read alongside docs/07-planning-and-reasoning/07.5-re-planning-when-things-fail.md.
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

# --------------------------------------------------------------------------- tools (fake data, as in 07-plan-and-execute)

VENUES = [
    {"id": "v1", "name": "Casa Azul", "city": "Lisbon", "capacity": 15, "day_rate_eur": 900},
    {"id": "v2", "name": "LX Loft", "city": "Lisbon", "capacity": 20, "day_rate_eur": 1100},
    {"id": "v3", "name": "Tejo Hall", "city": "Lisbon", "capacity": 40, "day_rate_eur": 2000},
]
BOOKED = {("v1", "2026-12-04")}  # Casa Azul is taken on 4 December


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

# --------------------------------------------------------------------------- plans


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


class GiveUp(Exception):
    """The planner says the goal cannot be reached."""


def parse_plan(text: str, finished: set[str] = frozenset()) -> list[Step]:
    """Parse and validate a plan. `finished` holds ids of steps already done, which new steps may depend on."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
        if "give_up" in data:
            raise GiveUp(data["give_up"])
        steps = [Step(id=s["id"], task=s["task"], depends_on=list(s.get("depends_on", [])),
                      done_when=s.get("done_when", "")) for s in data["steps"]]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PlanError(f"Plan is not valid JSON in the expected shape: {exc}") from exc
    ids = [s.id for s in steps]
    if not steps or len(ids) != len(set(ids)) or set(ids) & finished:
        raise PlanError("Plan must have at least one step, and new, unique step ids.")
    for s in steps:
        unknown = set(s.depends_on) - set(ids) - finished
        if unknown:
            raise PlanError(f"Step {s.id} depends on unknown steps {sorted(unknown)}.")
    try:
        batches(steps, finished)
    except CycleError as exc:
        raise PlanError(f"Plan has a dependency cycle: {exc.args[1]}") from exc
    return steps


def batches(steps: list[Step], finished: set[str] = frozenset()) -> list[list[str]]:
    """Dependency-ordered batches. Dependencies on already finished steps count as met."""
    sorter = TopologicalSorter({s.id: [d for d in s.depends_on if d not in finished] for s in steps})
    sorter.prepare()
    out: list[list[str]] = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        out.append(ready)
        sorter.done(*ready)
    return out


# --------------------------------------------------------------------------- prompts

PLANNER_SYSTEM = """You are a planner. Break the user's goal into 2-6 small steps that an assistant with these
tools can carry out: search_venues, check_availability, calculator.

Reply with JSON only: {"steps": [{"id": "s1", "task": "...", "depends_on": [], "done_when": "..."}]}
Each task does one thing; "done_when" says how to tell it is finished; depends_on lists the ids it needs."""

REPLANNER_SYSTEM = """You are a planner. A step of the current plan has FAILED.
Write a new plan for the REMAINING work only.

- Do not repeat finished steps. New steps may list finished step ids in depends_on to use their results.
- Do not retry the failed step unchanged. Use what the failure tells you to change approach.
- Use new step ids (r1, r2, ...).
- If the goal cannot be reached with these tools, reply {"give_up": "<one-sentence reason>"}.

Reply with JSON only: {"steps": [{"id": "r1", "task": "...", "depends_on": [], "done_when": "..."}]}"""

EXECUTOR_SYSTEM = """You carry out ONE step of a larger plan, using tools. Results of earlier steps are given to you.
When the step is finished, reply with text that starts with "DONE:" followed by the result in one or two sentences.
If you cannot meet the step's done-when criterion, reply "FAILED:" followed by the reason. Do not do other steps."""

ANSWER_SYSTEM = "Write the final answer to the user's goal from the step results. Be brief and give the key numbers."

# --------------------------------------------------------------------------- the agent


@dataclass
class ReplanningAgent:
    llm: LLM
    max_replans: int = 2
    max_tool_turns: int = 4  # per step
    log: list[str] = field(default_factory=list)
    finished: dict[str, Step] = field(default_factory=dict)

    def _log_plan(self, label: str, steps: list[Step]) -> None:
        for s in steps:
            after = f" (after {', '.join(s.depends_on)})" if s.depends_on else ""
            self.log.append(f"{label} {s.id}: {s.task}{after}")

    def plan(self, goal: str) -> list[Step]:
        steps = parse_plan(self.llm.chat([user(goal)], system=PLANNER_SYSTEM).text)
        self._log_plan("plan  ", steps)
        return steps

    def replan(self, goal: str, failed: Step) -> list[Step]:
        """Ask for a new plan for the rest of the work, given what is done and what failed."""
        done = "\n".join(f"- {s.id} ({s.task}): {s.result}" for s in self.finished.values()) or "(none)"
        prompt = (f"Goal: {goal}\n\nFinished steps:\n{done}\n\n"
                  f"FAILED step {failed.id} ({failed.task}): {failed.result}")
        steps = parse_plan(self.llm.chat([user(prompt)], system=REPLANNER_SYSTEM).text, set(self.finished))
        self._log_plan("replan", steps)
        return steps

    def execute_step(self, goal: str, step: Step) -> None:
        context = "\n".join(f"- {d}: {self.finished[d].result}" for d in step.depends_on) or "(none)"
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
                break
            for call in reply.tool_calls:
                fn, _ = TOOLS.get(call.name, (None, None))
                result = fn(**call.arguments) if fn else f"Error: unknown tool {call.name}"
                shown = result if len(result) <= 80 else result[:77] + "..."
                self.log.append(f"  tool {call.name}({call.arguments}) -> {shown}")
                messages.append(tool_result(call.id, result, is_error=result.startswith("Error")))
        else:
            step.status, step.result = "failed", f"no result after {self.max_tool_turns} tool turns"
        self.log.append(f"{step.status.upper():6} {step.id}: {step.result}")

    def execute(self, goal: str, steps: list[Step]) -> Step | None:
        """Run steps in dependency order. Return the first step that fails, or None."""
        by_id = {s.id: s for s in steps}
        for batch in batches(steps, set(self.finished)):
            for step_id in batch:
                step = by_id[step_id]
                self.execute_step(goal, step)
                if step.status == "failed":
                    return step
                self.finished[step.id] = step
        return None

    def run(self, goal: str) -> str:
        self.finished = {}
        steps = self.plan(goal)
        seen_failures: set[tuple[str, str]] = set()
        for attempt in range(self.max_replans + 1):
            failed = self.execute(goal, steps)
            if failed is None:
                break
            signature = (failed.task.lower(), failed.result.lower())
            if signature in seen_failures:
                return f"Gave up: step {failed.id} failed the same way twice ({failed.result})."
            seen_failures.add(signature)
            if attempt == self.max_replans:
                return f"Gave up after {self.max_replans} re-plans. Last failure: {failed.result}"
            try:
                steps = self.replan(goal, failed)
            except GiveUp as reason:
                self.log.append(f"GIVE UP: {reason}")
                return f"Gave up: {reason}"
        results = "\n".join(f"- {s.id} ({s.task}): {s.result}" for s in self.finished.values())
        return self.llm.chat([user(f"Goal: {goal}\n\nStep results:\n{results}")], system=ANSWER_SYSTEM).text


# --------------------------------------------------------------------------- demo script

GOAL = ("Find a venue in Lisbon for our 12-person offsite on 2026-12-04. Total budget is EUR 1,500, "
        "including lunch at EUR 25 per person. Which venue should we pick, and what is the total cost?")

PLAN_JSON = json.dumps({"steps": [
    {"id": "s1", "task": "Find Lisbon venues that hold at least 12 people", "depends_on": [],
     "done_when": "we have a list of venues with day rates"},
    {"id": "s2", "task": "Check the cheapest venue is free on 2026-12-04", "depends_on": ["s1"],
     "done_when": "one available venue and its day rate are known"},
    {"id": "s3", "task": "Work out lunch for 12 people at EUR 25 each", "depends_on": [],
     "done_when": "the lunch total in EUR is known"},
    {"id": "s4", "task": "Add venue rate and lunch, and compare with the EUR 1,500 budget",
     "depends_on": ["s2", "s3"], "done_when": "the total is known and we know if it is within budget"},
]})

REPLAN_JSON = json.dumps({"steps": [
    {"id": "r1", "task": "Check the next cheapest venue, LX Loft (v2), is free on 2026-12-04", "depends_on": ["s1"],
     "done_when": "LX Loft is confirmed available, or we know it is not"},
    {"id": "r2", "task": "Add LX Loft's rate and the lunch total, and compare with the EUR 1,500 budget",
     "depends_on": ["r1", "s3"], "done_when": "the total is known and we know if it is within budget"},
]})

SCRIPT = [
    PLAN_JSON,
    MockLLM.tool_call("search_venues", {"city": "Lisbon", "min_capacity": 12}),
    "DONE: Casa Azul (v1, EUR 900/day), LX Loft (v2, EUR 1,100/day) and Tejo Hall (v3, EUR 2,000/day) hold 12+.",
    MockLLM.tool_call("calculator", {"expression": "12 * 25"}),
    "DONE: Lunch costs EUR 300.",
    MockLLM.tool_call("check_availability", {"venue_id": "v1", "date": "2026-12-04"}),
    "FAILED: Casa Azul (v1) is already booked on 2026-12-04.",
    REPLAN_JSON,
    MockLLM.tool_call("check_availability", {"venue_id": "v2", "date": "2026-12-04"}),
    "DONE: LX Loft (v2) is available on 2026-12-04 at EUR 1,100.",
    MockLLM.tool_call("calculator", {"expression": "1100 + 300"}),
    "DONE: Total is EUR 1,400, which is EUR 100 under the EUR 1,500 budget.",
    "Casa Azul is booked on 4 December, so pick LX Loft: EUR 1,100 for the venue plus EUR 300 for lunch "
    "makes EUR 1,400, EUR 100 under budget.",
]


def main() -> None:
    agent = ReplanningAgent(get_llm(mock_responses=SCRIPT))
    print(f"Goal: {GOAL}\n")
    answer = agent.run(GOAL)
    print("\n".join(agent.log))
    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
