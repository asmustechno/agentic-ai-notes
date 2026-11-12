# 17 · Scheduling agent

A scheduling agent that finds a common slot for two people in different time zones, asks the user to confirm, and books it. While the user is confirming, someone else books one attendee, so the first booking attempt is refused and the agent proposes the next slot. Used in [17.5 Booking & scheduling agent](../../docs/17-case-studies/17.5-booking-and-scheduling-agent.md).

What to notice:

- **Confirmation is done by the app, not the model.** `Calendar.confirm()` is not a tool, so the model can't confirm on the user's behalf.
- **Double-booking guard.** `book` checks every calendar again at the moment of booking, not just when the slot was found.
- **Idempotency.** Calling `book` twice for the same proposal returns the same event.
- **Time zones.** Slots are stored in UTC and shown in each person's local time. The demo uses fixed offsets to stay dependency-free. Real code should use `zoneinfo`, because offsets change with daylight saving time (New York moves to UTC-4 on 14 March 2027).

## Run it

```bash
cd examples
python 17-scheduling-agent/main.py
```

Output (offline, with `MockLLM`):

```text
User:  Book a 45-minute design review with Ana and Ben on Tuesday 2027-03-09.
   find_slots(attendees=['ana', 'ben'], date=2027-03-09, duration_minutes=45) -> ok
   propose_booking(start_utc=2027-03-09T15:30:00+00:00, duration_minutes=45, attendees...) -> ok
Agent: How about Tue 9 Mar, 15:30-16:15 for Ana (Lisbon) and 10:30-11:15 for Ben (New York)? Please confirm.

User:  Yes, book it.
   book(proposal_id=P-1) -> REFUSED: Slot no longer free: ben is now busy (customer call). Find new slots and propose again.
   find_slots(attendees=['ana', 'ben'], date=2027-03-09, duration_minutes=45) -> ok
   propose_booking(start_utc=2027-03-09T16:00:00+00:00, duration_minutes=45, attendees...) -> ok
Agent: Sorry, Ben's 10:30 was just taken. Next option: 16:00-16:45 for Ana, 11:00-11:45 for Ben. Confirm?

User:  Yes.
   book(proposal_id=P-2) -> ok
Agent: Booked: Design review, Tue 9 Mar 16:00-16:45 Lisbon / 11:00-11:45 New York (EV-001).

Booked events: [{"event_id": "EV-001", "title": "Design review", "start_utc": "2027-03-09T16:00:00+00:00", "attendees": ["ana", "ben"]}]
```

## Test it

```bash
pytest 17-scheduling-agent
```

## Things to try

- Change the date to 2027-03-16 (after New York's clocks change) and switch `Person` to `zoneinfo.ZoneInfo`. Which slots move?
- Make proposals expire after 10 minutes, so an old "yes" can't book a stale slot.
- Add a `cancel(event_id)` tool. Should it need confirmation too?
