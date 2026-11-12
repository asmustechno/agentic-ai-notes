"""A supervisor agent that delegates to specialist agents exposed as tools.

    supervisor ──ask_flights_agent(task)──▶ flights agent ──search_flights──▶ fake flight API
               ──ask_hotels_agent(task)───▶ hotels agent  ──search_hotels───▶ fake hotel API

The supervisor never sees the flight or hotel APIs. It sees two tools whose
only argument is a written brief. Each specialist runs its own loop, with its
own instructions, tools and conversation, and hands back one short answer.

    python main.py                 # from this folder
    python 10-supervisor/main.py   # from examples/

Read alongside docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, Usage, get_llm, tool_result, user  # noqa: E402

Tool = tuple[Callable[..., str], ToolSpec]  # (the function, its description for the model)

# --------------------------------------------------------------------------- fake backends

FLIGHTS = [
    {"airline": "SkyLine", "out": "07:10", "back": "19:40", "price_eur": 182},
    {"airline": "TagusAir", "out": "09:25", "back": "21:05", "price_eur": 148},
    {"airline": "BlueJet", "out": "06:00", "back": "22:30", "price_eur": 161},
]
HOTELS = [
    {"name": "Casa Alfama", "price_per_night_eur": 75, "rating": 8.7},
    {"name": "Hotel Baixa Grande", "price_per_night_eur": 120, "rating": 9.1},
    {"name": "Rio Hostel Suites", "price_per_night_eur": 58, "rating": 7.4},
]


def search_flights(origin: str, destination: str, depart: str, return_date: str) -> str:
    """Return flights for a route (fake data: same list for every route)."""
    return json.dumps({"route": f"{origin}-{destination}", "depart": depart, "return": return_date, "options": FLIGHTS})


def search_hotels(city: str, check_in: str, nights: int, max_price_per_night: int) -> str:
    """Return hotels in a city at or under a nightly price (fake data)."""
    options = [h for h in HOTELS if h["price_per_night_eur"] <= max_price_per_night]
    return json.dumps({"city": city, "check_in": check_in, "nights": nights, "options": options})


SEARCH_FLIGHTS_SPEC: ToolSpec = {
    "name": "search_flights",
    "description": "Search return flights. Dates are YYYY-MM-DD. Returns airline, times and total return price in EUR.",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "depart": {"type": "string"},
            "return_date": {"type": "string"},
        },
        "required": ["origin", "destination", "depart", "return_date"],
    },
}
SEARCH_HOTELS_SPEC: ToolSpec = {
    "name": "search_hotels",
    "description": "Search hotels in a city. Returns name, nightly price in EUR and guest rating out of 10.",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "check_in": {"type": "string", "description": "YYYY-MM-DD"},
            "nights": {"type": "integer"},
            "max_price_per_night": {"type": "integer", "description": "EUR"},
        },
        "required": ["city", "check_in", "nights", "max_price_per_night"],
    },
}

# --------------------------------------------------------------------------- a small agent


@dataclass
class Agent:
    """One agent: a name, a model, instructions, tools and a bounded loop."""

    name: str
    llm: LLM
    instructions: str
    tools: dict[str, Tool] = field(default_factory=dict)
    max_steps: int = 6
    usage: Usage = field(default_factory=Usage)  # tokens this agent used, summed over its calls
    trace: list[str] = field(default_factory=list)  # shared between agents to show one timeline
    depth: int = 0  # indentation in the trace: 0 = supervisor, 1 = specialist

    def _log(self, line: str) -> None:
        self.trace.append("    " * self.depth + f"[{self.name}] {line}")

    def run(self, task: str) -> str:
        messages: list[Message] = [user(task)]  # a fresh conversation: context isolation
        specs = [spec for _, spec in self.tools.values()]
        for step in range(1, self.max_steps + 1):
            reply = self.llm.chat(messages, system=self.instructions, tools=specs or None)
            self.usage.input_tokens += reply.usage.input_tokens
            self.usage.output_tokens += reply.usage.output_tokens
            messages.append(reply.to_message())
            if not reply.tool_calls:
                self._log(f"answer: {_clip(reply.text)}")
                return reply.text
            for call in reply.tool_calls:
                if call.name not in self.tools:
                    messages.append(tool_result(call.id, f"Unknown tool {call.name!r}", is_error=True))
                    continue
                self._log(f"step {step}: {call.name}({_short(call.arguments)})")
                fn, _ = self.tools[call.name]
                messages.append(tool_result(call.id, fn(**call.arguments)))
        return f"{self.name} stopped at the step limit without an answer."


def _clip(text: str, limit: int = 70) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _short(args: dict) -> str:
    return _clip(json.dumps(args, ensure_ascii=False))


def as_tool(agent: Agent, name: str, description: str) -> Tool:
    """Wrap an agent so another agent can call it like any other tool.

    The only thing that crosses the boundary is the `task` string going in and
    the final answer coming out. The specialist's tool calls stay in its own
    conversation, so they never fill up the supervisor's context window.
    """

    def call_agent(task: str) -> str:
        return agent.run(task)

    spec: ToolSpec = {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "A complete, self-contained brief: the objective, the facts needed, "
                    "the output format and any limits. The specialist sees nothing else.",
                }
            },
            "required": ["task"],
        },
    }
    return call_agent, spec


# --------------------------------------------------------------------------- the team

SUPERVISOR_PROMPT = (
    "You plan trips. You cannot search flights or hotels yourself: delegate to the specialists. "
    "Give each one a complete brief (dates, cities, budget, what to return), because they cannot see this "
    "conversation. Call independent specialists in the same turn. Then combine their answers into one plan, "
    "check it fits the budget, and reply in at most four sentences."
)
FLIGHTS_PROMPT = "You find flights. Use search_flights. Reply with the single best option that fits the brief, in one sentence."
HOTELS_PROMPT = "You find hotels. Use search_hotels. Reply with the single best option that fits the brief, in one sentence."

GOAL = "Plan a weekend in Lisbon from London, Friday 2027-03-12 to Sunday 2027-03-14. Budget: 400 EUR for flights and hotel."

FLIGHTS_BRIEF = (
    "Find the cheapest return flight London to Lisbon, out 2027-03-12, back 2027-03-14. "
    "Return airline, times and total price in EUR."
)
HOTELS_BRIEF = (
    "Find a hotel in Lisbon for 2 nights from 2027-03-12, at most 80 EUR per night, guest rating 8 or more. "
    "Return name, nightly price and total in EUR."
)

SCRIPTS: dict[str, list] = {
    "supervisor": [
        MockLLM.tool_calls([("ask_flights_agent", {"task": FLIGHTS_BRIEF}), ("ask_hotels_agent", {"task": HOTELS_BRIEF})]),
        "Fly TagusAir (out 09:25 Friday, back 21:05 Sunday) for 148 EUR and stay two nights at Casa Alfama "
        "(rated 8.7) for 150 EUR. Total: 298 EUR, which leaves 102 EUR of your 400 EUR budget.",
    ],
    "flights": [
        MockLLM.tool_call(
            "search_flights", {"origin": "London", "destination": "Lisbon", "depart": "2027-03-12", "return_date": "2027-03-14"}
        ),
        "Cheapest: TagusAir, out 09:25, back 21:05, 148 EUR return.",
    ],
    "hotels": [
        MockLLM.tool_call("search_hotels", {"city": "Lisbon", "check_in": "2027-03-12", "nights": 2, "max_price_per_night": 80}),
        "Casa Alfama: 75 EUR per night, rated 8.7, 150 EUR for 2 nights.",
    ],
}


def build_team(llms: dict[str, LLM]) -> tuple[Agent, dict[str, Agent]]:
    """Create the two specialists and a supervisor whose only tools are those specialists."""
    trace: list[str] = []
    flights = Agent("flights", llms["flights"], FLIGHTS_PROMPT, {"search_flights": (search_flights, SEARCH_FLIGHTS_SPEC)}, trace=trace, depth=1)
    hotels = Agent("hotels", llms["hotels"], HOTELS_PROMPT, {"search_hotels": (search_hotels, SEARCH_HOTELS_SPEC)}, trace=trace, depth=1)
    supervisor = Agent(
        "supervisor",
        llms["supervisor"],
        SUPERVISOR_PROMPT,
        {
            "ask_flights_agent": as_tool(flights, "ask_flights_agent", "Delegate a flight search to the flights specialist."),
            "ask_hotels_agent": as_tool(hotels, "ask_hotels_agent", "Delegate a hotel search to the hotels specialist."),
        },
        trace=trace,
    )
    return supervisor, {"flights": flights, "hotels": hotels}


def main() -> None:
    # One model client per agent. With a real provider they are identical; with MockLLM each gets its own script.
    llms = {name: get_llm(mock_responses=script) for name, script in SCRIPTS.items()}
    supervisor, specialists = build_team(llms)
    print(f"Goal: {GOAL}\n")
    answer = supervisor.run(GOAL)
    print("\n".join(supervisor.trace))
    print(f"\nAnswer: {answer}\n")
    print("Tokens (estimated by MockLLM unless you use a real provider):")
    total = 0
    for agent in [supervisor, *specialists.values()]:
        used = agent.usage.input_tokens + agent.usage.output_tokens
        total += used
        print(f"  {agent.name:<10} {used:>5}")
    print(f"  {'total':<10} {total:>5}")


if __name__ == "__main__":
    main()
