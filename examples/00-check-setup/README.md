# 00 · Check your setup

Confirms Python, your installed packages and your model provider all work. Used in [0.3 Setup](../../docs/00-start-here/00.3-setup.md).

## Run it

```bash
cd examples
python 00-check-setup/main.py
```

Expected output with the default `LLM_PROVIDER=mock`:

```text
Python:   3.11.9
Provider: mock
Model:    mock-model
Reply:    Hello! Your setup works (offline, with MockLLM).
Tokens:   8 in, 12 out

✅ Ready. Next: read docs/01-foundations or run the tests with `pytest`.
```

With a real provider, `Provider`, `Model` and `Reply` change, and the token counts become exact.

## Test it

```bash
pytest 00-check-setup
```
