# 09 · Prompt chaining

A changelog becomes a translated user announcement in three fixed LLM calls (extract, write, translate), with plain-Python gates between them that stop the chain early on bad output. Used in [9.1 Prompt chaining](../../docs/09-agent-design-patterns/09.1-prompt-chaining.md).

## Run it

```bash
cd examples
python 09-prompt-chaining/main.py
```

Output (offline, with `MockLLM`):

```text
step 1 extract   -> 3 user-facing changes (gate passed)
step 2 write     -> 33 words (gate passed)
step 3 translate -> done

English:
New this week: unused money in your monthly budgets can now roll over to next month, the reports page has a dark mode, and CSV exports keep every row, even ones with emoji.

Spanish:
Novedades de esta semana: el dinero que no uses en tus presupuestos mensuales ahora puede pasar al mes siguiente, la página de informes tiene modo oscuro y las exportaciones CSV conservan todas las filas, incluso las que tienen emojis.
```

Each step gets only the previous step's output, not the whole history. If a gate fails (not JSON, too long, internal jargon), the chain raises `GateFailed` and the later steps never run, so no money is spent on bad input.

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 09-prompt-chaining
```

## Things to try

- Script step 1 to return prose instead of JSON. Where does the chain stop?
- Add a fourth step that writes a push-notification title of at most 40 characters, with its own gate.
- Which gate could you turn into a retry instead of a hard stop?
