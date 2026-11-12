"""Shared state: two agents work on one blackboard without overwriting each other.

    scout_a ─┐                       ┌─ read_board()  -> what this agent may see
             ├─▶  Blackboard  ◀──────┤
    scout_b ─┘   (versioned keys)    └─ write_board(key, value, expected_version)

Both scouts run at the same time (the scheduler interleaves their steps). Both
read the empty shortlist, both try to write it. The board uses *optimistic
concurrency*: a write must say which version it read. The second write is
rejected with a clear error, so that agent re-reads and merges instead of
silently erasing the other agent's work. The board also enforces who may
read and write each key, and keeps an append-only log of every change.

    python main.py                   # from this folder
    python 10-shared-state/main.py   # from examples/

Read alongside docs/10-multi-agent-systems/10.4-shared-state-and-communication.md.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- the blackboard


@dataclass
class Entry:
    value: str
    version: int
    author: str


@dataclass
class Blackboard:
    """A small key-value store with versions, permissions and a change log."""

    entries: dict[str, Entry] = field(default_factory=dict)
    can_read: dict[str, set[str]] = field(default_factory=dict)  # agent -> keys it may read
    can_write: dict[str, set[str]] = field(default_factory=dict)  # agent -> keys it may write
    log: list[str] = field(default_factory=list)

    def read(self, agent: str) -> dict[str, dict]:
        """The agent's *view*: only the keys it is allowed to see."""
        allowed = self.can_read.get(agent, set())
        return {k: {"value": e.value, "version": e.version, "author": e.author} for k, e in self.entries.items() if k in allowed}

    def write(self, agent: str, key: str, value: str, expected_version: int) -> tuple[bool, str]:
        """Compare-and-set: succeed only if the key is still at the version the agent read."""
        if key not in self.can_write.get(agent, set()):
            self.log.append(f"DENIED   {agent} -> {key}")
            return False, f"Permission denied: {agent} may not write {key!r}."
        current = self.entries.get(key)
        current_version = current.version if current else 0
        if current_version != expected_version:
            self.log.append(f"CONFLICT {agent} -> {key} (expected v{expected_version}, found v{current_version})")
            return False, (
                f"Version conflict on {key!r}: you read v{expected_version} but it is now v{current_version}, "
                f"written by {current.author if current else '?'}: {current.value if current else ''!r}. "
                "Read the board again and merge your change; do not drop their work."
            )
        self.entries[key] = Entry(value, current_version + 1, agent)
        self.log.append(f"WRITE    {agent} -> {key} v{current_version + 1}: " + value.replace("\n", " | "))
        return True, f"Saved {key!r} as v{current_version + 1}."


READ_SPEC: ToolSpec = {
    "name": "read_board",
    "description": "Read the shared board. Returns each key you may see with its value, version and author.",
    "input_schema": {"type": "object", "properties": {}},
}
WRITE_SPEC: ToolSpec = {
    "name": "write_board",
    "description": (
        "Write one key on the shared board. Pass the version you last read (0 if the key does not exist). "
        "If someone changed it since, the write fails: read again and merge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
            "expected_version": {"type": "integer"},
        },
        "required": ["key", "value", "expected_version"],
    },
}

# --------------------------------------------------------------------------- agents that step one model call at a time


@dataclass
class BoardAgent:
    name: str
    llm: LLM
    instructions: str
    board: Blackboard
    messages: list[Message] = field(default_factory=list)
    done: bool = False
    answer: str = ""

    def step(self, trace: list[str]) -> None:
        """One model call plus the tools it asks for. The scheduler decides who goes next."""
        reply = self.llm.chat(self.messages, system=self.instructions, tools=[READ_SPEC, WRITE_SPEC])
        self.messages.append(reply.to_message())
        if not reply.tool_calls:
            self.done, self.answer = True, reply.text
            trace.append(f"[{self.name}] done: {reply.text}")
            return
        for call in reply.tool_calls:
            if call.name == "read_board":
                view = self.board.read(self.name)
                result, ok = json.dumps(view), True
                trace.append(f"[{self.name}] read_board -> " + ", ".join(f"{k} v{v['version']}" for k, v in view.items()))
            elif call.name == "write_board":
                a = call.arguments
                ok, result = self.board.write(self.name, a["key"], a["value"], int(a["expected_version"]))
                trace.append(f"[{self.name}] write_board({a['key']!r}, v{a['expected_version']}) -> {result.split(':')[0]}")
            else:
                ok, result = False, f"Unknown tool {call.name!r}"
            self.messages.append(tool_result(call.id, result, is_error=not ok))


def run_interleaved(agents: list[BoardAgent], max_rounds: int = 8) -> list[str]:
    """Round-robin: each unfinished agent takes one step per round, as if they ran in parallel."""
    trace: list[str] = []
    for r in range(1, max_rounds + 1):
        active = [a for a in agents if not a.done]
        if not active:
            break
        trace.append(f"-- round {r}")
        for agent in active:
            agent.step(trace)
    return trace


# --------------------------------------------------------------------------- the scenario

BRIEF = "Team offsite for 40 people, 12-13 May 2027, venue budget at most 3500 EUR."
SCOUT_PROMPT = (
    "You scout offsite venues in {city}. Read the board first. Add your best venue to the 'shortlist' key "
    "as one line per venue. Keep every venue already on the shortlist. Never write other keys."
)

VENUE_A = "Casa Alfama, Lisbon: 40 people, 3200 EUR"
VENUE_B = "Quinta do Rio, Porto: 45 people, 2900 EUR"

SCRIPTS: dict[str, list] = {
    "scout_a": [
        MockLLM.tool_call("read_board"),
        MockLLM.tool_call("write_board", {"key": "shortlist", "value": VENUE_A, "expected_version": 0}),
        "Added Casa Alfama to the shortlist.",
    ],
    "scout_b": [
        MockLLM.tool_call("read_board"),
        MockLLM.tool_call("write_board", {"key": "shortlist", "value": VENUE_B, "expected_version": 0}),
        MockLLM.tool_call("read_board"),  # after the conflict: re-read
        MockLLM.tool_call("write_board", {"key": "shortlist", "value": f"{VENUE_A}\n{VENUE_B}", "expected_version": 1}),
        "Merged Quinta do Rio into the shortlist, keeping Casa Alfama.",
    ],
}


def build(llms: dict[str, LLM]) -> tuple[Blackboard, list[BoardAgent]]:
    board = Blackboard(
        entries={
            "brief": Entry(BRIEF, 1, "user"),
            "budget_notes": Entry("Finance only: we may stretch to 3800 EUR if needed.", 1, "finance"),
        },
        can_read={"scout_a": {"brief", "shortlist"}, "scout_b": {"brief", "shortlist"}},
        can_write={"scout_a": {"shortlist"}, "scout_b": {"shortlist"}},
    )
    agents = [
        BoardAgent("scout_a", llms["scout_a"], SCOUT_PROMPT.format(city="Lisbon"), board, [user("Find one venue in Lisbon.")]),
        BoardAgent("scout_b", llms["scout_b"], SCOUT_PROMPT.format(city="Porto"), board, [user("Find one venue in Porto.")]),
    ]
    return board, agents


def main() -> None:
    llms = {name: get_llm(mock_responses=script) for name, script in SCRIPTS.items()}
    board, agents = build(llms)
    print("\n".join(run_interleaved(agents)))
    print("\nChange log:")
    print("\n".join(f"  {line}" for line in board.log))
    print("\nFinal shortlist (v{}):".format(board.entries["shortlist"].version))
    print(board.entries["shortlist"].value)


if __name__ == "__main__":
    main()
