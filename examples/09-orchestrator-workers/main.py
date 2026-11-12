"""Orchestrator-workers: a lead model decides the sub-tasks at run time, workers do them, the lead combines.

    task -> [orchestrator: plan]  -> JSON list of sub-tasks (how many depends on the task) -> validate
         -> [worker] [worker] ... (one call per sub-task, run concurrently)
         -> [orchestrator: synthesise] -> one summary

Unlike sectioning (09.3), the split is not fixed in code: a one-line fix gets one sub-task,
a feature touching four files gets four.

    python main.py                           # from this folder
    python 09-orchestrator-workers/main.py   # from examples/

Read alongside docs/09-agent-design-patterns/09.4-orchestrator-workers.md.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, get_llm, user  # noqa: E402

REPO_FILES = [
    "app/models/user.py",
    "app/auth/login.py",
    "app/admin/templates/users.html",
    "migrations/",
    "tests/test_login.py",
    "README.md",
]
MAX_SUBTASKS = 6

ORCHESTRATOR_SYSTEM = (
    "You are the lead engineer. Break the task into the smallest set of independent sub-tasks, one per file "
    "to change. Only use files from this list: " + ", ".join(REPO_FILES) + ". "
    'Reply with JSON only: {"subtasks": [{"file": "...", "instruction": "..."}]}'
)
WORKER_SYSTEM = (
    "You are an engineer changing ONE file. Describe the exact change in one or two lines. "
    "Do not mention other files."
)
SYNTH_SYSTEM = "You are the lead engineer. Combine the workers' changes into a short pull-request description."


class PlanError(Exception):
    """The orchestrator's plan was unusable."""


@dataclass
class Subtask:
    file: str
    instruction: str


@dataclass
class OrchestratorResult:
    plan: list[Subtask]
    worker_outputs: list[str]
    summary: str


def parse_plan(text: str) -> list[Subtask]:
    """Validate the plan before spending money on workers."""
    try:
        items = json.loads(text)["subtasks"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PlanError(f"plan is not the expected JSON: {exc}") from exc
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_SUBTASKS:
        raise PlanError(f"plan must have 1 to {MAX_SUBTASKS} sub-tasks")
    plan = []
    for item in items:
        if not isinstance(item, dict) or item.get("file") not in REPO_FILES or not item.get("instruction"):
            raise PlanError(f"invalid sub-task (unknown file or missing instruction): {item}")
        plan.append(Subtask(item["file"], item["instruction"]))
    if len({s.file for s in plan}) != len(plan):
        raise PlanError("two sub-tasks change the same file; workers would conflict")
    return plan


def orchestrate(task: str, orchestrator: LLM, worker: LLM, *, max_workers: int = 4) -> OrchestratorResult:
    # 1. Plan: the orchestrator decides what the sub-tasks are, based on this input.
    plan = parse_plan(orchestrator.chat([user(task)], system=ORCHESTRATOR_SYSTEM).text)

    # 2. Work: each worker gets the overall goal plus only its own sub-task.
    def do(sub: Subtask) -> str:
        prompt = f"Overall goal: {task}\nYour file: {sub.file}\nYour sub-task: {sub.instruction}"
        return worker.chat([user(prompt)], system=WORKER_SYSTEM).text.strip()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        outputs = list(pool.map(do, plan))  # map keeps the plan's order

    # 3. Synthesise: the orchestrator sees every result and writes one answer.
    report = "\n".join(f"- {s.file}: {out}" for s, out in zip(plan, outputs))
    summary = orchestrator.chat([user(f"Task: {task}\n\nChanges made:\n{report}")], system=SYNTH_SYSTEM).text.strip()
    return OrchestratorResult(plan, outputs, summary)


# ---------------------------------------------------------------- an offline demo

FEATURE = "Record when each user last logged in, and show it on the admin users page."
TYPO = "Fix the typo 'recieve' in the README."

PLANS = {
    FEATURE: {
        "subtasks": [
            {"file": "app/models/user.py", "instruction": "Add a nullable last_login timestamp field."},
            {"file": "migrations/", "instruction": "Add a migration that creates the last_login column."},
            {"file": "app/auth/login.py", "instruction": "Set last_login to the current UTC time on success."},
            {"file": "app/admin/templates/users.html", "instruction": "Add a 'Last login' column."},
            {"file": "tests/test_login.py", "instruction": "Test that a successful login sets last_login."},
        ]
    },
    TYPO: {"subtasks": [{"file": "README.md", "instruction": "Replace 'recieve' with 'receive'."}]},
}
WORKER_REPLIES = {
    "app/models/user.py": "Added `last_login = Column(DateTime(timezone=True), nullable=True)` to User.",
    "migrations/": "New migration 0042_add_last_login adds a nullable last_login column to users.",
    "app/auth/login.py": "After a successful password check, set `user.last_login = datetime.now(UTC)` and save.",
    "app/admin/templates/users.html": "Added a 'Last login' column showing the date, or 'never' if empty.",
    "tests/test_login.py": "Added test_successful_login_sets_last_login and test_failed_login_leaves_it_unchanged.",
    "README.md": "Changed 'recieve' to 'receive' in the Notifications section.",
}


def mock_orchestrator(messages: list[Message]) -> str:
    """Plans by task, or synthesises when it is shown the workers' changes."""
    text = messages[-1]["content"]
    if text.startswith("Task:"):
        n = text.count("\n- ")
        return f"This change touches {n} file{'s' if n != 1 else ''}:\n" + text.split("Changes made:\n", 1)[1]
    return json.dumps(PLANS[text])


def mock_worker(messages: list[Message]) -> str:
    file = messages[-1]["content"].split("Your file: ", 1)[1].split("\n", 1)[0]
    return WORKER_REPLIES[file]


def main() -> None:
    orchestrator = get_llm(mock_responses=[mock_orchestrator] * 4)
    worker = orchestrator if not isinstance(orchestrator, MockLLM) else MockLLM([mock_worker] * 6)
    for task in (FEATURE, TYPO):
        result = orchestrate(task, orchestrator, worker)
        print(f"Task: {task}")
        print(f"  orchestrator planned {len(result.plan)} sub-task(s):")
        for sub in result.plan:
            print(f"    - {sub.file}: {sub.instruction}")
        print("  summary:\n    " + result.summary.replace("\n", "\n    ") + "\n")


if __name__ == "__main__":
    main()
