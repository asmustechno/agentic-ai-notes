# 05 · Episodic, semantic and procedural memory

An email-drafting agent with three separate memory stores. Used in [5.4 Episodic, semantic & procedural memory](../../docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md) and [5.5 Memory design trade-offs](../../docs/05-memory/05.5-memory-design-trade-offs.md).

| Store | Holds | Example | How it's updated |
| --- | --- | --- | --- |
| Semantic | Facts | `manager: Priya` | Newest value for a key replaces the old one; `forget(key)` deletes |
| Episodic | Past runs | `run 1 (needs_revision): too long, buried the blocker` | One entry appended per run |
| Procedural | How to do the job | `Status emails: under 30 words, blockers first.` | New rules appended, duplicates skipped |

After each run, a **reflection** call asks the model to return JSON saying what to keep. Personal data (emails, phone numbers) is redacted before anything is stored. Before each run, the agent builds its system prompt from all three stores.

## Run it

```bash
cd examples
python 05-memory-types/main.py
```

Output (offline, with `MockLLM`):

```text
RUN 1: Draft this week's status email for my manager.
  draft: 37 words
  feedback: Too long. Keep it under 30 words and always list blockers first. FYI my manager is Priya (priya.shah@example.com) and we are the Platform team.

MEMORY AFTER RUN 1
  semantic:   manager = Priya ([email]); team = Platform team
  episodic:   run 1 [needs_revision] Drafted the weekly status email; it was too long and buried the blocker.
  procedural: Status emails: under 30 words, blockers first.

RUN 2 (a week later): Draft this week's status email for my manager.
  system prompt the model received:
    You draft short internal emails for the user. Follow the procedures. Use the facts. Learn from past episodes.

    <procedures>
    - Status emails: under 30 words, blockers first.
    </procedures>

    <facts>
    - manager: Priya ([email])
    - team: Platform team
    </facts>

    <past_episodes>
    - run 1 (needs_revision): Drafted the weekly status email; it was too long and buried the blocker.
    </past_episodes>
  draft (24 words):
    Hi Priya,

    Blockers: staging cluster still down (ops ticket open).

    Done: login page shipped, database migration finished.

    Next: sprint planning on Monday.

    Platform team

  episodes now: [(1, 'needs_revision'), (2, 'success')]
```

## Test it

```bash
pytest 05-memory-types
```

## Things to try

- Add a cap: keep only the five most recent episodes. Where should older ones go?
- Make the reflection reply invalid JSON in `SCRIPT`. What does memory look like afterwards? (Nothing changes, on purpose.)
- Store procedures in a file the user can read and edit. That is roughly what Anthropic's memory tool does: see [5.4](../../docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md).
