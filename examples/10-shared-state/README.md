# 10 · Shared state

Two scout agents add venues to one shared shortlist at the same time. The shared board uses versions (optimistic concurrency), so the second writer gets a clear conflict error, re-reads and merges, and no work is lost. The board also controls what each agent may read and write, and logs every change. Used in [10.4 Shared state & communication](../../docs/10-multi-agent-systems/10.4-shared-state-and-communication.md).

What to notice:

- Round 1: both scouts read the board before either writes. That is the classic lost-update set-up.
- Round 2: `scout_b`'s write says "I read v0", but the key is now v1, so it is rejected with the other agent's value in the error.
- `budget_notes` is on the board, but neither scout can see it: each agent gets a *view*.
- The change log is append-only, so you can replay who changed what and when.

## Run it

```bash
cd examples
python 10-shared-state/main.py
```

Output (offline, with `MockLLM`):

```text
-- round 1
[scout_a] read_board -> brief v1
[scout_b] read_board -> brief v1
-- round 2
[scout_a] write_board('shortlist', v0) -> Saved 'shortlist' as v1.
[scout_b] write_board('shortlist', v0) -> Version conflict on 'shortlist'
-- round 3
[scout_a] done: Added Casa Alfama to the shortlist.
[scout_b] read_board -> brief v1, shortlist v1
-- round 4
[scout_b] write_board('shortlist', v1) -> Saved 'shortlist' as v2.
-- round 5
[scout_b] done: Merged Quinta do Rio into the shortlist, keeping Casa Alfama.

Change log:
  WRITE    scout_a -> shortlist v1: Casa Alfama, Lisbon: 40 people, 3200 EUR
  CONFLICT scout_b -> shortlist (expected v0, found v1)
  WRITE    scout_b -> shortlist v2: Casa Alfama, Lisbon: 40 people, 3200 EUR | Quinta do Rio, Porto: 45 people, 2900 EUR

Final shortlist (v2):
Casa Alfama, Lisbon: 40 people, 3200 EUR
Quinta do Rio, Porto: 45 people, 2900 EUR
```

## Test it

```bash
pytest 10-shared-state
```

## Things to try

- Remove the version check in `Blackboard.write` and run the tests. Which one catches the lost update?
- Give each scout its own key (`shortlist_lisbon`, `shortlist_porto`) instead. Do you still need versions?
- Add a `finance` agent that can read `budget_notes` and writes a `decision` key that only it may write.
