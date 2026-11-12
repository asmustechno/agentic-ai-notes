# 10 · Supervisor

A supervisor agent that plans a trip by delegating to two specialist agents, a flights agent and a hotels agent. Each specialist is exposed to the supervisor as an ordinary tool whose only argument is a written brief. Used in [10.2 Supervisor & hierarchical](../../docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md).

What to notice:

- The supervisor's tools are `ask_flights_agent` and `ask_hotels_agent`. It never sees the search APIs.
- Each specialist starts a **fresh conversation** containing only the brief. It cannot see the user's message, so the brief must be complete.
- Raw search results stay inside the specialist. Only its one-line answer reaches the supervisor (context isolation).
- Three agents means three bills: the token table at the end adds up every agent's calls.

## Run it

```bash
cd examples
python 10-supervisor/main.py
```

Output (offline, with `MockLLM`):

```text
Goal: Plan a weekend in Lisbon from London, Friday 2027-03-12 to Sunday 2027-03-14. Budget: 400 EUR for flights and hotel.

[supervisor] step 1: ask_flights_agent({"task": "Find the cheapest return flight London to Lisbon, out 202...)
    [flights] step 1: search_flights({"origin": "London", "destination": "Lisbon", "depart": "2027-03-12...)
    [flights] answer: Cheapest: TagusAir, out 09:25, back 21:05, 148 EUR return.
[supervisor] step 1: ask_hotels_agent({"task": "Find a hotel in Lisbon for 2 nights from 2027-03-12, at m...)
    [hotels] step 1: search_hotels({"city": "Lisbon", "check_in": "2027-03-12", "nights": 2, "max_pric...)
    [hotels] answer: Casa Alfama: 75 EUR per night, rated 8.7, 150 EUR for 2 nights.
[supervisor] answer: Fly TagusAir (out 09:25 Friday, back 21:05 Sunday) for 148 EUR and ...

Answer: Fly TagusAir (out 09:25 Friday, back 21:05 Sunday) for 148 EUR and stay two nights at Casa Alfama (rated 8.7) for 150 EUR. Total: 298 EUR, which leaves 102 EUR of your 400 EUR budget.

Tokens (estimated by MockLLM unless you use a real provider):
  supervisor   385
  flights      234
  hotels       215
  total        834
```

## Test it

```bash
pytest 10-supervisor
```

## Things to try

- Run the two specialists in parallel with `concurrent.futures.ThreadPoolExecutor` when the supervisor asks for both in one turn.
- Make the brief vague (just "find flights") and run it with a real model. What does the flights agent ask or assume?
- Add a third specialist, `ask_budget_agent`, that checks the total against the budget, and decide whether it is worth the extra tokens.
