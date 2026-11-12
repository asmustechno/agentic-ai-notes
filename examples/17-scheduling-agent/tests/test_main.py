"""Confirmation step, double-booking guard and idempotent booking. Offline, with MockLLM."""

import json
from datetime import datetime, timedelta

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def block_ben(cal, start: str = "2027-03-09T15:30:00+00:00", minutes: int = 30) -> None:
    at = datetime.fromisoformat(start)
    cal.people["ben"].busy.append((at, at + timedelta(minutes=minutes), "customer call"))


def test_slots_respect_busy_times_and_everyones_working_hours() -> None:
    ok, result = main.build_calendar().find_slots(["ana", "ben"], "2027-03-09", 45)
    slots = json.loads(result)
    assert ok and [s["start_utc"] for s in slots] == [
        "2027-03-09T15:30:00+00:00", "2027-03-09T15:45:00+00:00", "2027-03-09T16:00:00+00:00"]
    assert slots[0]["local_times"] == {"ana": "Tue 09 Mar 15:30-16:15", "ben": "Tue 09 Mar 10:30-11:15"}


def test_after_a_clash_the_next_free_slot_is_found() -> None:
    cal = main.build_calendar()
    block_ben(cal)
    slots = json.loads(cal.find_slots(["ana", "ben"], "2027-03-09", 45)[1])
    assert slots[0]["start_utc"] == main.SLOT_2


def test_model_cannot_book_without_user_confirmation() -> None:
    cal = main.build_calendar()
    cal.propose_booking(main.SLOT_1, 45, ["ana", "ben"], "Review")
    ok, msg = cal.book("P-1")
    assert not ok and "not confirmed" in msg and cal.events == []


def test_double_booking_guard_rechecks_at_booking_time() -> None:
    cal = main.build_calendar()
    cal.propose_booking(main.SLOT_1, 45, ["ana", "ben"], "Review")
    cal.confirm("P-1")
    block_ben(cal)
    ok, msg = cal.book("P-1")
    assert not ok and "no longer free" in msg and cal.events == []


def test_booking_is_idempotent() -> None:
    cal = main.build_calendar()
    cal.propose_booking(main.SLOT_2, 45, ["ana", "ben"], "Review")
    cal.confirm("P-1")
    first, second = cal.book("P-1"), cal.book("P-1")
    assert first[0] and second[0] and "already booked" in second[1]
    assert len(cal.events) == 1
    assert sum(t == "Review" for _, _, t in cal.people["ana"].busy) == 1


def test_full_conversation() -> None:
    cal = main.build_calendar()
    llm = MockLLM(main.SCRIPT)
    agent = main.SchedulingAgent(llm, cal)
    assert "confirm" in agent.turn(main.REQUEST).lower()
    assert cal.events == []  # nothing booked before the user says yes
    cal.confirm("P-1")
    block_ben(cal)
    agent.turn("Yes, book it.")
    assert any("REFUSED: Slot no longer free" in line for line in agent.trace)
    cal.confirm("P-2")
    assert "EV-001" in agent.turn("Yes.")
    assert [e["start_utc"] for e in cal.events] == [main.SLOT_2]
    assert llm.calls[-1]["messages"][0]["content"] == main.REQUEST  # the conversation carries across turns


def test_unknown_attendee() -> None:
    ok, msg = main.build_calendar().find_slots(["ana", "zoe"], "2027-03-09", 30)
    assert not ok and "zoe" in msg
