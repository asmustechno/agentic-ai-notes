"""A resumable agent: checkpoint after every step in SQLite, resume after a crash without repeating work.

    python main.py                          # from this folder
    python 15-resumable-agent/main.py       # from examples/

Read alongside docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md.

Two ideas make this work:
  1. Save the whole run state (the messages and the step counter) after every
     model reply and every tool result. The next action is always decided from
     the saved state, so "resume" is just "load and keep going".
  2. Give every side-effecting tool an idempotency key built from the run id and
     the tool call id. Both are saved, so a tool re-run after a crash sends the
     same key and the outside system can ignore the repeat.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolCall, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- saving messages as JSON


def encode_messages(messages: list[Message]) -> str:
    """Turn the neutral message list into JSON. ToolCall objects become plain dicts."""
    out = []
    for m in messages:
        m = dict(m)
        if "tool_calls" in m:
            m["tool_calls"] = [asdict(tc) for tc in m["tool_calls"]]
        if "_raw" in m:  # Anthropic content blocks (may include thinking blocks): keep them, as dicts
            blocks = m["_raw"]["content"]
            m["_raw"] = {
                "provider": m["_raw"]["provider"],
                "content": [b.model_dump(mode="json", exclude_none=True) if hasattr(b, "model_dump") else b for b in blocks],
            }
        out.append(m)
    return json.dumps(out)


def decode_messages(data: str) -> list[Message]:
    """The reverse of encode_messages."""
    messages = json.loads(data)
    for m in messages:
        if "tool_calls" in m:
            m["tool_calls"] = [ToolCall(**tc) for tc in m["tool_calls"]]
    return messages


# --------------------------------------------------------------------------- the checkpoint store (stdlib sqlite3)


@dataclass
class RunState:
    run_id: str
    goal: str
    messages: list[Message] = field(default_factory=list)
    step: int = 0  # model calls made so far (persisted, so the step limit survives crashes)
    status: str = "running"  # running | done | failed
    answer: str | None = None
    resumes: int = 0  # how many times this run was picked up again after a crash


class CheckpointStore:
    """One row per run. Every save replaces the row inside a transaction, so a crash never leaves half a save."""

    def __init__(self, path: str | Path) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer; safe on crash
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                   run_id TEXT PRIMARY KEY, goal TEXT NOT NULL, messages TEXT NOT NULL,
                   step INTEGER NOT NULL, status TEXT NOT NULL, answer TEXT,
                   resumes INTEGER NOT NULL, updated_at REAL NOT NULL)"""
        )

    def save(self, s: RunState) -> None:
        with self.db:  # commits on success, rolls back on error
            self.db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s.run_id, s.goal, encode_messages(s.messages), s.step, s.status, s.answer, s.resumes, time.time()),
            )

    def load(self, run_id: str) -> RunState | None:
        row = self.db.execute(
            "SELECT run_id, goal, messages, step, status, answer, resumes FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return RunState(row[0], row[1], decode_messages(row[2]), row[3], row[4], row[5], row[6])

    def close(self) -> None:
        self.db.close()


# --------------------------------------------------------------------------- tools, one with a side effect


@dataclass
class Outbox:
    """A fake email service that, like a good API, ignores a repeated idempotency key."""

    sent: list[dict[str, str]] = field(default_factory=list)
    keys: set[str] = field(default_factory=set)

    def send(self, to: str, subject: str, body: str, idempotency_key: str) -> str:
        if idempotency_key in self.keys:
            return f"already sent (key {idempotency_key})"
        self.keys.add(idempotency_key)
        self.sent.append({"to": to, "subject": subject, "body": body})
        return f"sent to {to}"


SALES = {"2026-W45": {"orders": 1284, "revenue_gbp": 48210}}

TOOLS: list[ToolSpec] = [
    {
        "name": "get_sales",
        "description": "Read-only. Get order count and revenue for an ISO week like '2026-W45'.",
        "input_schema": {"type": "object", "properties": {"week": {"type": "string"}}, "required": ["week"]},
    },
    {
        "name": "send_email",
        "description": "Send an email. Has a side effect: call it once per message.",
        "input_schema": {
            "type": "object",
            "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
            "required": ["to", "subject", "body"],
        },
    },
]
SYSTEM = "You write and send the weekly sales report. Get the numbers with get_sales, then email them with send_email."


class SimulatedCrash(Exception):
    """Stands in for the process dying: a deploy, an out-of-memory kill, a lost machine."""


# --------------------------------------------------------------------------- the resumable agent


@dataclass
class ResumableAgent:
    llm: LLM
    store: CheckpointStore
    outbox: Outbox
    max_steps: int = 8
    max_resumes: int = 3  # a run that keeps crashing at the same place is marked failed, not retried forever
    on_event: Callable[[str], None] = lambda event: None  # tests and the demo use this to inject crashes
    log: list[str] = field(default_factory=list)

    def run_tool(self, run_id: str, call: ToolCall) -> str:
        if call.name == "get_sales":
            return json.dumps(SALES.get(call.arguments["week"], {}))
        if call.name == "send_email":
            key = f"{run_id}:{call.id}"  # stable: both parts are in the checkpoint
            return self.outbox.send(**call.arguments, idempotency_key=key)
        return f"Error: unknown tool {call.name}"

    def run(self, run_id: str, goal: str) -> str:
        state = self.store.load(run_id)
        if state is None:
            state = RunState(run_id, goal, messages=[user(goal)])
            self.store.save(state)
        elif state.status != "running":
            return state.answer or ""  # already finished: never redo a finished run
        else:
            state.resumes += 1
            self.log.append(f"resume {run_id} at step {state.step} ({len(state.messages)} messages saved)")
            if state.resumes > self.max_resumes:
                state.status, state.answer = "failed", "Gave up: the run crashed too many times."
            self.store.save(state)  # save the resume count now, or a crash loop would never reach the limit
            if state.status == "failed":
                return state.answer or ""

        while True:
            pending = self.pending_tool_calls(state.messages)
            if pending:  # the last reply asked for tools we have not finished: run them
                for call in pending:
                    result = self.run_tool(run_id, call)
                    self.log.append(f"step {state.step}: {call.name} -> {result}")
                    self.on_event(f"tool_ran:{call.name}")  # a crash here = side effect done, result not saved
                    state.messages.append(tool_result(call.id, result))
                    self.store.save(state)
                    self.on_event(f"tool_saved:{call.name}")
                continue

            if state.step >= self.max_steps:
                state.status, state.answer = "failed", "Stopped: step limit reached."
                self.store.save(state)
                return state.answer

            reply = self.llm.chat(state.messages, system=SYSTEM, tools=TOOLS)
            self.on_event(f"model_replied:{state.step + 1}")  # a crash here = this reply is lost and paid for again
            state.step += 1
            state.messages.append(reply.to_message())
            if not reply.tool_calls:
                state.status, state.answer = "done", reply.text
            self.store.save(state)
            self.log.append(f"step {state.step}: model -> {', '.join(c.name for c in reply.tool_calls) or 'answer'} (saved)")
            self.on_event(f"saved:{state.step}")
            if state.status == "done":
                return reply.text

    @staticmethod
    def pending_tool_calls(messages: list[Message]) -> list[ToolCall]:
        """Tool calls in the most recent assistant message that have no result yet."""
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "assistant":
                done = {m["tool_call_id"] for m in messages[i + 1 :] if m["role"] == "tool"}
                return [c for c in messages[i].get("tool_calls", []) if c.id not in done]
        return []


# --------------------------------------------------------------------------- demo

GOAL = "Send the 2026-W45 sales report to team@example.com."
SCRIPT = [
    MockLLM.tool_call("get_sales", {"week": "2026-W45"}),
    MockLLM.tool_call(
        "send_email",
        {"to": "team@example.com", "subject": "Sales 2026-W45", "body": "1,284 orders, £48,210 revenue."},
    ),
    "Sent the 2026-W45 report to team@example.com: 1,284 orders and £48,210 revenue.",
]


def crash_once_at(event_name: str) -> Callable[[str], None]:
    """An on_event hook that raises SimulatedCrash the first time `event_name` happens."""
    fired = False

    def hook(event: str) -> None:
        nonlocal fired
        if event == event_name and not fired:
            fired = True
            raise SimulatedCrash(event)

    return hook


def demo(crash_at: str, db_path: Path) -> None:
    llm, outbox = get_llm(mock_responses=SCRIPT), Outbox()
    store = CheckpointStore(db_path)
    first = ResumableAgent(llm, store, outbox, on_event=crash_once_at(crash_at))
    try:
        first.run("run-42", GOAL)
    except SimulatedCrash as exc:
        print("\n".join(f"  {line}" for line in first.log))
        print(f"  CRASH at {exc}")
    store.close()  # the process is gone; only the database survives

    store = CheckpointStore(db_path)  # a new process (or another worker) picks the run up
    second = ResumableAgent(llm, store, outbox)
    answer = second.run("run-42", GOAL)
    print("\n".join(f"  {line}" for line in second.log))
    print(f"  answer: {answer}")
    print(f"  emails actually sent: {len(outbox.sent)}")
    store.close()


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        print("A) Crash right after send_email's result was saved")
        demo("tool_saved:send_email", Path(tmp) / "a.db")
        print("\nB) Crash after the email went out but BEFORE its result was saved")
        demo("tool_ran:send_email", Path(tmp) / "b.db")


if __name__ == "__main__":
    main()
