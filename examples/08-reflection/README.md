# 08 · The reflection pattern

One model drafts a release note, critiques it with a separate critic prompt, and revises it until the critic replies `NO ISSUES` or a round limit is hit. Used in [8.1 The reflection pattern](../../docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md).

## Run it

```bash
cd examples
python 08-reflection/main.py
```

Output (offline, with `MockLLM`):

```text
Task: Write a release note for version 2.3. It fixes the bug where CSV exports were sometimes empty.

--- draft 1
v2.3: Fixed a race condition in the CSV serializer that caused zero-byte exports.

--- critique 1
- Jargon: 'race condition', 'serializer' and 'zero-byte' mean nothing to most users.
- Does not say what the user should do if an earlier export was empty.

--- draft 2
Version 2.3 fixes a problem that sometimes made exported spreadsheets (CSV files) empty. If an export you made recently was blank, please export it again.

--- critique 2
NO ISSUES

Stopped: critic found no issues. Model calls: 4
```

The critic runs in a fresh conversation with its own system prompt, so it judges the draft rather than defending it. The loop stops on a strict `NO ISSUES` reply, or after `max_rounds` critiques.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 08-reflection
```

## Things to try

- Set `max_rounds=1` and script a critic that never says `NO ISSUES`. Which draft comes back?
- Make the critic's checklist stricter (for example "one sentence only") and script a third round.
- Run it with a real model (`LLM_PROVIDER=anthropic` or `openai`) and count the rounds.
