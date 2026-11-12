"""A scheduling agent: find a slot, ask the user, then book it safely.

    find_slots ─▶ propose_booking ─▶ (user clicks Confirm, in the app) ─▶ book
                                                                         │
                                         re-checks every calendar ◀──────┘  (double-booking guard)

Three rules live in code, not in the prompt:
  1. `book` works only for a proposal the *user* confirmed. The model cannot confirm for them.
  2. `book` re-checks every attendee's calendar at booking time, because a slot
     that was free a minute ago may not be free now.
  3. Booking the same proposal twice returns the same event (idempotent), so a retry never double-books.

Times are stored in UTC and shown in each person's local time. To stay
dependency-free the demo uses fixed UTC offsets; real code should use
`zoneinfo.ZoneInfo("Europe/Lisbon")` so daylight-saving changes are handled.

    python main.py                         # from this folder
    python 17-scheduling-agent/main.py     # from examples/

Read alongside docs/17-case-studies/17.5-booking-and-scheduling-agent.md.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

UTC = timezone.utc
WORK_START, WORK_END = 9, 17  # local working hours
STEP = timedelta(minutes=15)  # slot grid


@dataclass
class Person:
    name: str
    utc_offset: int  # hours; fixed for the demo (real code: zoneinfo)
    busy: list[tuple[datetime, datetime, str]] = field(default_factory=list)

    @property
    def tz(self) -> timezone:
        return timezone(timedelta(hours=self.utc_offset))

    def is_free(self, start: datetime, end: datetime) -> bool:
        return all(end <= b_start or start >= b_end for b_start, b_end, _ in self.busy)

    def in_working_hours(self, start: datetime, end: datetime) -> bool:
        s, e = start.astimezone(self.tz), end.astimezone(self.tz)
        return s.date() == e.date() and WORK_START <= s.hour and (e.hour, e.minute) <= (WORK_END, 0)


@dataclass
class Proposal:
    id: str
    start: datetime
    end: datetime
    attendees: list[str]
    title: str
    confirmed: bool = False  # set only by the app, when the user clicks Confirm
    event_id: str | None = None


@dataclass
class Calendar:
    people: dict[str, Person]
    proposals: dict[str, Proposal] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    # ---- tools the model may call

    def find_slots(self, attendees: list[str], date: str, duration_minutes: int) -> tuple[bool, str]:
        unknown = [a for a in attendees if a not in self.people]
        if unknown:
            return False, f"Unknown attendee(s): {unknown}. Known: {sorted(self.people)}"
        length = timedelta(minutes=duration_minutes)
        t = datetime.fromisoformat(date).replace(tzinfo=UTC) - timedelta(hours=12)  # scan the whole day for every zone
        end_of_scan = t + timedelta(hours=48)
        slots = []
        while t + length <= end_of_scan and len(slots) < 3:
            people = [self.people[a] for a in attendees]
            if all(p.in_working_hours(t, t + length) and p.is_free(t, t + length) for p in people) and t.date().isoformat() == date:
                slots.append(self._describe(t, t + length, attendees))
            t += STEP
        return True, json.dumps(slots) if slots else "No common free slot that day. Try another date."

    def propose_booking(self, start_utc: str, duration_minutes: int, attendees: list[str], title: str) -> tuple[bool, str]:
        start = datetime.fromisoformat(start_utc).astimezone(UTC)
        end = start + timedelta(minutes=duration_minutes)
        pid = f"P-{len(self.proposals) + 1}"
        self.proposals[pid] = Proposal(pid, start, end, attendees, title)
        return True, json.dumps({"proposal_id": pid, **self._describe(start, end, attendees),
                                 "next": "Ask the user to confirm. Do not call book until they have."})

    def book(self, proposal_id: str) -> tuple[bool, str]:
        p = self.proposals.get(proposal_id)
        if p is None:
            return False, f"No proposal {proposal_id!r}."
        if p.event_id:  # idempotent: a retry returns the same event
            return True, json.dumps({"event_id": p.event_id, "status": "already booked"})
        if not p.confirmed:
            return False, "The user has not confirmed this proposal. Ask them first."
        clashes = [f"{n} is now busy ({title})" for n in p.attendees
                   for b_start, b_end, title in self.people[n].busy if not (p.end <= b_start or p.start >= b_end)]
        if clashes:  # double-booking guard: check again at the moment of booking
            return False, "Slot no longer free: " + "; ".join(clashes) + ". Find new slots and propose again."
        p.event_id = f"EV-{len(self.events) + 1:03d}"
        for n in p.attendees:
            self.people[n].busy.append((p.start, p.end, p.title))
        self.events.append({"event_id": p.event_id, "title": p.title, "start_utc": p.start.isoformat(), "attendees": p.attendees})
        return True, json.dumps({"event_id": p.event_id, "status": "booked", **self._describe(p.start, p.end, p.attendees)})

    # ---- called by the app, never by the model

    def confirm(self, proposal_id: str) -> None:
        self.proposals[proposal_id].confirmed = True

    def _describe(self, start: datetime, end: datetime, attendees: list[str]) -> dict:
        local = {n: f"{start.astimezone(self.people[n].tz):%a %d %b %H:%M}-{end.astimezone(self.people[n].tz):%H:%M}" for n in attendees}
        return {"start_utc": start.isoformat(), "local_times": local}


SPECS: list[ToolSpec] = [
    {
        "name": "find_slots",
        "description": "Find up to 3 slots on a date (YYYY-MM-DD) when all attendees are free and inside their working hours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "attendees": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
                "duration_minutes": {"type": "integer"},
            },
            "required": ["attendees", "date", "duration_minutes"],
        },
    },
    {
        "name": "propose_booking",
        "description": "Create a proposal for one slot. Does NOT book. The user must confirm it in the app first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_utc": {"type": "string", "description": "ISO 8601, from find_slots"},
                "duration_minutes": {"type": "integer"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "title": {"type": "string"},
            },
            "required": ["start_utc", "duration_minutes", "attendees", "title"],
        },
    },
    {
        "name": "book",
        "description": "Book a proposal the user has confirmed. Fails if it is unconfirmed or the slot is no longer free.",
        "input_schema": {"type": "object", "properties": {"proposal_id": {"type": "string"}}, "required": ["proposal_id"]},
    },
]

PROMPT = (
    "You schedule meetings. Always use find_slots; never invent times. Propose one slot with propose_booking, "
    "then show it to the user in each attendee's local time and ask them to confirm. Only call book after the "
    "user has confirmed. If booking fails because the slot was taken, find new slots and propose again."
)


@dataclass
class SchedulingAgent:
    llm: LLM
    calendar: Calendar
    messages: list[Message] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    max_steps: int = 6

    def turn(self, text: str) -> str:
        """One user turn: loop until the model replies to the user (it keeps the conversation between turns)."""
        self.messages.append(user(text))
        for _ in range(self.max_steps):
            reply = self.llm.chat(self.messages, system=PROMPT, tools=SPECS)
            self.messages.append(reply.to_message())
            if not reply.tool_calls:
                return reply.text
            for call in reply.tool_calls:
                fn = getattr(self.calendar, call.name, None) if call.name in {s["name"] for s in SPECS} else None
                ok, result = fn(**call.arguments) if fn else (False, f"Unknown tool {call.name!r}")
                self.trace.append(f"{call.name}({_brief(call.arguments)}) -> {'ok' if ok else 'REFUSED: ' + result}")
                self.messages.append(tool_result(call.id, result, is_error=not ok))
        return "Sorry, I could not finish that. Please try again."


def _brief(args: dict) -> str:
    text = ", ".join(f"{k}={v}" for k, v in args.items() if k != "title")
    return text if len(text) <= 70 else text[:67] + "..."


# --------------------------------------------------------------------------- the demo

def build_calendar() -> Calendar:
    d = "2027-03-09"
    at = lambda hhmm: datetime.fromisoformat(f"{d}T{hhmm}:00+00:00")  # noqa: E731  (UTC times)
    return Calendar({
        "ana": Person("Ana", 0, [(at("14:00"), at("15:00"), "1:1")]),  # Lisbon in March: UTC+0
        "ben": Person("Ben", -5, [(at("15:00"), at("15:30"), "standup")]),  # New York in early March: UTC-5
    })


REQUEST = "Book a 45-minute design review with Ana and Ben on Tuesday 2027-03-09."
SLOT_1, SLOT_2 = "2027-03-09T15:30:00+00:00", "2027-03-09T16:00:00+00:00"
SCRIPT = [
    # turn 1: find and propose
    MockLLM.tool_call("find_slots", {"attendees": ["ana", "ben"], "date": "2027-03-09", "duration_minutes": 45}),
    MockLLM.tool_call("propose_booking", {"start_utc": SLOT_1, "duration_minutes": 45, "attendees": ["ana", "ben"], "title": "Design review"}),
    "How about Tue 9 Mar, 15:30-16:15 for Ana (Lisbon) and 10:30-11:15 for Ben (New York)? Please confirm.",
    # turn 2: user confirmed, but the slot was taken meanwhile
    MockLLM.tool_call("book", {"proposal_id": "P-1"}),
    MockLLM.tool_call("find_slots", {"attendees": ["ana", "ben"], "date": "2027-03-09", "duration_minutes": 45}),
    MockLLM.tool_call("propose_booking", {"start_utc": SLOT_2, "duration_minutes": 45, "attendees": ["ana", "ben"], "title": "Design review"}),
    "Sorry, Ben's 10:30 was just taken. Next option: 16:00-16:45 for Ana, 11:00-11:45 for Ben. Confirm?",
    # turn 3: confirmed again
    MockLLM.tool_call("book", {"proposal_id": "P-2"}),
    "Booked: Design review, Tue 9 Mar 16:00-16:45 Lisbon / 11:00-11:45 New York (EV-001).",
]


def main() -> None:
    cal = build_calendar()
    agent = SchedulingAgent(get_llm(mock_responses=SCRIPT), cal)

    def say(text: str) -> None:
        before = len(agent.trace)
        print(f"User:  {text}")
        answer = agent.turn(text)
        for line in agent.trace[before:]:
            print(f"   {line}")
        print(f"Agent: {answer}\n")

    say(REQUEST)
    cal.confirm("P-1")  # the user clicks "Confirm" in the app...
    at = datetime.fromisoformat("2027-03-09T15:30:00+00:00")
    cal.people["ben"].busy.append((at, at + timedelta(minutes=30), "customer call"))  # ...but someone books Ben first
    say("Yes, book it.")
    cal.confirm("P-2")
    say("Yes.")
    print("Booked events:", json.dumps(cal.events))


if __name__ == "__main__":
    main()
