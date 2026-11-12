# 07 · Plan-and-execute

A planner writes the whole plan first, as JSON (steps with ids, dependencies and "done when" criteria). Our code validates it, works out the order with `graphlib.TopologicalSorter`, and an executor carries out one step at a time with tools. A last call writes the answer. Used in [7.2 Plan-and-execute](../../docs/07-planning-and-reasoning/07.2-plan-and-execute.md) and [7.3 Task decomposition](../../docs/07-planning-and-reasoning/07.3-task-decomposition.md).

## Run it

```bash
cd examples
python 07-plan-and-execute/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Find a venue in Lisbon for our 12-person offsite on 2026-12-03. Total budget is EUR 1,500, including lunch at EUR 25 per person. Which venue should we pick, and what is the total cost?

plan  s1: Find Lisbon venues that hold at least 12 people
plan  s2: Check the cheapest venue is free on 2026-12-03 (after s1)
plan  s3: Work out lunch for 12 people at EUR 25 each
plan  s4: Add venue rate and lunch, and compare with the EUR 1,500 budget (after s2, s3)
order [s1, s3] -> [s2] -> [s4]
  tool search_venues({'city': 'Lisbon', 'min_capacity': 12}) -> [{"id": "v1", "name": "Casa Azul", "city": "Lisbon", "capacity": 15, "day_rat...
done  s1: Casa Azul (v1, EUR 900/day), LX Loft (v2, EUR 1,100/day) and Tejo Hall (v3, EUR 2,000/day) hold 12+.
  tool calculator({'expression': '12 * 25'}) -> 300
done  s3: Lunch costs EUR 300.
  tool check_availability({'venue_id': 'v1', 'date': '2026-12-03'}) -> {"venue_id": "v1", "date": "2026-12-03", "available": true}
done  s2: Casa Azul (v1) is available on 2026-12-03 at EUR 900.
  tool calculator({'expression': '900 + 300'}) -> 1200
done  s4: Total is EUR 1,200, which is EUR 300 under the EUR 1,500 budget.

Answer: Book Casa Azul on 3 December: EUR 900 for the venue plus EUR 300 for lunch makes EUR 1,200, EUR 300 under budget.
```

What to notice:

- `order [s1, s3] -> [s2] -> [s4]`: steps s1 and s3 don't depend on each other, so they share a batch and could run in parallel.
- The planner call has **no tools**: it only plans. Each executor call sees its own step plus the results of the steps it depends on, nothing else.
- Every step must end with `DONE:` or `FAILED:`. Here a failure stops the run; [`07-replanning`](../07-replanning/README.md) recovers instead.

## Test it

```bash
pytest 07-plan-and-execute
```

## Things to try

- In `SCRIPT`, change the reply that finishes s2 to `"FAILED: Casa Azul is booked."`. What does the run return, and how many model calls were made?
- Make the planner return a plan with a cycle (s2 depends on s4). Where is it caught?
- Add a `book_venue` tool. Which step should it be, and what should its `done_when` say?
