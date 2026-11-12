# 08 · Self-critique with tests

The model writes `slugify()`, the code runs fixed tests in a separate Python process with a timeout, and the exact failure output goes back to the model. The first attempt fails two tests; the second passes. Used in [8.3 Self-critique with tests](../../docs/08-reflection-and-self-correction/08.3-self-critique-with-tests.md).

## Run it

```bash
cd examples
python 08-self-critique-with-tests/main.py
```

Output (offline, with `MockLLM`):

```text
--- attempt 1
def slugify(title: str) -> str:
    return "-".join(title.lower().split())

test output:
FAIL slugify('Hello, World!'): expected 'hello-world', got 'hello,-world!'
FAIL slugify('Agents 101: a guide'): expected 'agents-101-a-guide', got 'agents-101:-a-guide'

--- attempt 2
import re

def slugify(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return "-".join(words)

test output:
PASS: all 4 tests passed

Result: tests pass after 2 attempt(s).
```

The tests, not the model, decide when the code is done. With the default `MockLLM` the executed code is scripted and known to be safe. **With a real model this runs model-written code**: `main.py` refuses unless you set `ALLOW_CODE_EXECUTION=1`, and you should only do that inside a disposable container or VM. A subprocess with a timeout stops infinite loops; it is not a sandbox (see [13.3](../../docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md)).

Set `LLM_PROVIDER=anthropic` or `openai` in `examples/.env` to run the same code with a real model.

## Test it

```bash
pytest 08-self-critique-with-tests
```

## Things to try

- Add the test case `("Café au lait", "cafe-au-lait")`. Does attempt 2 still pass? What would the model see?
- Read `test_infinite_loop_is_killed_by_the_timeout`. What would happen without `timeout=`?
- Change the loop to send only the latest failure instead of the whole conversation. What does the model lose?
