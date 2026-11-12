# 07 · Re-planning when a step fails

The offsite task from [`07-plan-and-execute`](../07-plan-and-execute/README.md), on a date when the cheapest venue is already booked. When step s2 fails, the agent keeps the finished steps, sends the failure to a re-planner, and runs the new plan for the remaining work. Used in [7.5 Re-planning when things fail](../../docs/07-planning-and-reasoning/07.5-re-planning-when-things-fail.md).

Limits: at most `max_replans` new plans; the same step failing for the same reason twice stops the run; and the planner can reply `{"give_up": "..."}`.

## Run it

```bash
cd examples
python 07-replanning/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Find a venue in Lisbon for our 12-person offsite on 2026-12-04. Total budget is EUR 1,500, including lunch at EUR 25 per person. Which venue should we pick, and what is the total cost?

plan   s1: Find Lisbon venues that hold at least 12 people
plan   s2: Check the cheapest venue is free on 2026-12-04 (after s1)
plan   s3: Work out lunch for 12 people at EUR 25 each
plan   s4: Add venue rate and lunch, and compare with the EUR 1,500 budget (after s2, s3)
  tool search_venues({'city': 'Lisbon', 'min_capacity': 12}) -> [{"id": "v1", "name": "Casa Azul", "city": "Lisbon", "capacity": 15, "day_rat...
DONE   s1: Casa Azul (v1, EUR 900/day), LX Loft (v2, EUR 1,100/day) and Tejo Hall (v3, EUR 2,000/day) hold 12+.
  tool calculator({'expression': '12 * 25'}) -> 300
DONE   s3: Lunch costs EUR 300.
  tool check_availability({'venue_id': 'v1', 'date': '2026-12-04'}) -> {"venue_id": "v1", "date": "2026-12-04", "available": false}
FAILED s2: Casa Azul (v1) is already booked on 2026-12-04.
replan r1: Check the next cheapest venue, LX Loft (v2), is free on 2026-12-04 (after s1)
replan r2: Add LX Loft's rate and the lunch total, and compare with the EUR 1,500 budget (after r1, s3)
  tool check_availability({'venue_id': 'v2', 'date': '2026-12-04'}) -> {"venue_id": "v2", "date": "2026-12-04", "available": true}
DONE   r1: LX Loft (v2) is available on 2026-12-04 at EUR 1,100.
  tool calculator({'expression': '1100 + 300'}) -> 1400
DONE   r2: Total is EUR 1,400, which is EUR 100 under the EUR 1,500 budget.

Answer: Casa Azul is booked on 4 December, so pick LX Loft: EUR 1,100 for the venue plus EUR 300 for lunch makes EUR 1,400, EUR 100 under budget.
```

What to notice:

- s1 and s3 are **not** rerun: the new steps r1 and r2 depend on them by id.
- The new plan changes approach (check the next venue) instead of retrying the failed step.
- The original s4 is gone: r2 replaces it, using LX Loft's price.

## Test it

```bash
pytest 07-replanning
```

The tests also cover giving up: every venue booked, `max_replans` reached, the planner's `give_up` reply, and the same failure repeating.

## Things to try

- Set `max_replans=0`. What does the run return now?
- Make the re-planner's new plan fail too (book `v2` in `BOOKED`) and write the script for a second re-plan to Tejo Hall. Is EUR 2,300 within budget? What should the agent say?
