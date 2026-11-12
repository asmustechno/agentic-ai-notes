"""Self-critique with tests: let real test results, not the model's opinion, decide what to fix.

    1. the model writes a function
    2. our code runs fixed tests against it in a separate process, with a timeout
    3. if a test fails, the exact failure output goes back to the model
    4. repeat until the tests pass or attempts run out

    python main.py                                 # from this folder
    python 08-self-critique-with-tests/main.py     # from examples/

SAFETY: this runs code written by a model. A subprocess with a timeout stops runaway loops,
but it is NOT a sandbox: the code can still read files or use the network. With the default
MockLLM the code is scripted and known to be safe. With a real model, main() refuses to run
unless you set ALLOW_CODE_EXECUTION=1, and you should only do that inside a disposable
container or VM. See docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md.

Read alongside docs/08-reflection-and-self-correction/08.3-self-critique-with-tests.md.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, MockLLM, get_llm, user  # noqa: E402

TASK = (
    "Write a Python function `slugify(title: str) -> str` that turns a blog post title into a URL slug: "
    "lowercase, words joined by single hyphens, and only the characters a-z, 0-9 and '-'. "
    "No leading or trailing hyphens. Reply with one ```python code block only."
)

# The tests are written by us, not by the model, and the model cannot change them.
TESTS = '''
CASES = [
    ("Hello World", "hello-world"),
    ("  Many   spaces  ", "many-spaces"),
    ("Hello, World!", "hello-world"),
    ("Agents 101: a guide", "agents-101-a-guide"),
]
failures = []
for arg, want in CASES:
    try:
        got = slugify(arg)
    except Exception as exc:  # report crashes as failures, with the error
        got = f"raised {type(exc).__name__}: {exc}"
    if got != want:
        failures.append(f"FAIL slugify({arg!r}): expected {want!r}, got {got!r}")
print("\\n".join(failures) or f"PASS: all {len(CASES)} tests passed")
raise SystemExit(1 if failures else 0)
'''

ATTEMPT_1 = '''```python
def slugify(title: str) -> str:
    return "-".join(title.lower().split())
```'''
ATTEMPT_2 = '''```python
import re

def slugify(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return "-".join(words)
```'''
SCRIPT = [ATTEMPT_1, ATTEMPT_2]


@dataclass
class CheckResult:
    passed: bool
    output: str


@dataclass
class Attempt:
    code: str
    run: CheckResult


@dataclass
class FixResult:
    passed: bool
    code: str
    attempts: list[Attempt] = field(default_factory=list)


def extract_code(reply: str) -> str:
    """Take the first ```python block, or the whole reply if there is none."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", reply, re.S)
    return (match.group(1) if match else reply).strip()


def run_tests(code: str, *, timeout: float = 10.0) -> CheckResult:
    """Run `code` followed by TESTS in a fresh Python process, and report what happened."""
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "check.py"
        script.write_text(code + "\n\n" + TESTS, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script)],  # -I: isolated mode, ignores PYTHON* env vars and user site-packages
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,  # kills infinite loops
            )
        except subprocess.TimeoutExpired:
            return CheckResult(False, f"TIMEOUT: the code did not finish within {timeout} seconds.")
    output = (proc.stdout + proc.stderr).strip()
    return CheckResult(proc.returncode == 0, output[-2000:])  # keep the end: that is where errors are


def solve_with_tests(llm: LLM, task: str, *, max_attempts: int = 3, timeout: float = 10.0) -> FixResult:
    """Ask for code, run the tests, feed failures back, and repeat."""
    messages = [user(task)]
    attempts: list[Attempt] = []
    for _ in range(max_attempts):
        reply = llm.chat(messages)
        code = extract_code(reply.text)
        result = run_tests(code, timeout=timeout)
        attempts.append(Attempt(code, result))
        if result.passed:
            return FixResult(True, code, attempts)
        messages += [  # keep the conversation, so the model sees its own code and the real failures
            reply.to_message(),
            user(f"I ran the tests. They failed with this output:\n\n{result.output}\n\n"
                 "Fix the function. Reply with one ```python code block only."),
        ]
    return FixResult(False, attempts[-1].code, attempts)


def main() -> None:
    llm = get_llm(mock_responses=SCRIPT)
    if not isinstance(llm, MockLLM) and os.getenv("ALLOW_CODE_EXECUTION") != "1":
        sys.exit("Refusing to run model-written code. Set ALLOW_CODE_EXECUTION=1 only inside a sandbox.")

    result = solve_with_tests(llm, TASK)
    for i, attempt in enumerate(result.attempts, start=1):
        print(f"--- attempt {i}\n{attempt.code}\n")
        print(f"test output:\n{attempt.run.output}\n")
    print(f"Result: {'tests pass' if result.passed else 'still failing'} after {len(result.attempts)} attempt(s).")


if __name__ == "__main__":
    main()
