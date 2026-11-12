"""Code execution as a tool: the model writes Python, we run it in a separate process with limits.

    python main.py                      # from this folder
    python 03-code-execution/main.py    # from examples/

IMPORTANT: a subprocess is NOT a security sandbox. It limits time and output and
hides your environment variables, but the code still runs as you, with your
files and your network. Only run model-written code like this on a machine or
container you are happy to lose. For untrusted input use real isolation: a
container with no network, gVisor, a Firecracker microVM, or a hosted sandbox
such as Anthropic's code execution tool or OpenAI's Code Interpreter.

Read alongside docs/03-tools-and-function-calling/03.6-code-execution-as-a-tool.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, get_llm, tool_result, user  # noqa: E402


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int | None  # None if we had to kill it
    timed_out: bool = False

    def for_model(self) -> str:
        """A compact report for the model: what happened, then the (trimmed) output."""
        status = "timed out and was killed" if self.timed_out else f"exit code {self.exit_code}"
        parts = [f"[{status}]"]
        if self.stdout:
            parts.append(f"stdout:\n{self.stdout}")
        if self.stderr:
            parts.append(f"stderr:\n{self.stderr}")
        return "\n".join(parts)


def _trim(text: str | bytes | None, limit: int) -> str:
    """Keep output small: the model pays for every character, and huge output hides the useful part."""
    if text is None:
        return ""
    if isinstance(text, bytes):  # TimeoutExpired always carries bytes
        text = text.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[output truncated: showing {limit} of {len(text)} characters]"


def _limit_resources(memory_mb: int, cpu_seconds: int):  # pragma: no cover - runs in the child, POSIX only
    """Return a function that sets hard limits in the child process before Python starts."""

    def apply() -> None:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 * 1024,) * 2)  # address space (memory)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))  # CPU time
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))  # open files
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024,) * 2)  # largest file it may write

    return apply


def run_python(code: str, *, timeout: float = 5.0, max_output: int = 4_000, memory_mb: int = 512) -> ExecResult:
    """Run `code` with a fresh Python interpreter in an empty temporary folder.

    What this does:  wall-clock timeout (the process is killed), output caps,
    no inherited environment variables (so no API keys), an empty working
    folder that is deleted afterwards, isolated mode (-I) so it ignores
    PYTHON* variables and the user's site-packages, no stdin, and on Linux/macOS
    memory, CPU, file-size and open-file limits.
    What this does NOT do:  stop file access outside the folder, stop network
    access, or stop anything else your user account is allowed to do.
    """
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]  # Windows needs this for Python to start
    extra = {}
    if os.name == "posix":
        extra["preexec_fn"] = _limit_resources(memory_mb, cpu_seconds=int(timeout) + 1)

    with tempfile.TemporaryDirectory(prefix="agent-code-") as workdir:
        script = Path(workdir) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script)],
                cwd=workdir, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout, **extra,
            )
        except subprocess.TimeoutExpired as exc:  # subprocess.run kills the child for us
            return ExecResult(_trim(exc.stdout, max_output), _trim(exc.stderr, max_output), None, timed_out=True)
    # Show "snippet.py" in tracebacks, not the temporary path (which also reveals your user name).
    stderr = proc.stderr.replace(str(script), "snippet.py")
    return ExecResult(_trim(proc.stdout, max_output), _trim(stderr, max_output), proc.returncode)


RUN_PYTHON_SPEC = {
    "name": "run_python",
    "description": (
        "Run a short Python 3 script and return its exit code, stdout and stderr. Use it for arithmetic, "
        "statistics and data processing instead of calculating in your head. Print the values you need: "
        "only printed output comes back. Standard library only, no network, no files kept between calls, "
        "5 second time limit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "A complete Python script."}},
        "required": ["code"],
        "additionalProperties": False,
    },
}


def run_agent(llm: LLM, goal: str, max_steps: int = 5, log: list[str] | None = None) -> str:
    messages: list[Message] = [user(goal)]
    for _ in range(max_steps):
        reply = llm.chat(messages, tools=[RUN_PYTHON_SPEC])
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text
        for call in reply.tool_calls:
            if call.name != "run_python" or "code" not in call.arguments:
                messages.append(tool_result(call.id, "Call run_python with a 'code' string.", is_error=True))
                continue
            result = run_python(call.arguments["code"])
            if log is not None:
                log.append(f"code:\n{call.arguments['code']}\nresult:\n{result.for_model()}")
            # A script that crashed is still a useful observation: the model reads the traceback and fixes it.
            messages.append(tool_result(call.id, result.for_model(), is_error=result.timed_out))
    return "Stopped: step limit reached."


GOAL = "Delivery times this week were 12, 15, 11, 30 and 14 minutes. What are the mean and standard deviation, and is any value an outlier?"
CODE_1 = """import statistics as st
times = [12, 15, 11, 30, 14]
print(st.mean(times), st.stdev(times))
print(stats.median(times))
"""
CODE_2 = """import statistics as st
times = [12, 15, 11, 30, 14]
mean, sd = st.mean(times), st.stdev(times)
print(f"mean={mean:.1f} sd={sd:.2f}")
print("z-scores:", {t: round((t - mean) / sd, 2) for t in times})
"""
SCRIPT = [
    MockLLM.tool_call("run_python", {"code": CODE_1}),  # has a bug: `stats` is not defined
    MockLLM.tool_call("run_python", {"code": CODE_2}),
    "The mean is 16.4 minutes and the standard deviation is about 7.77 minutes. The 30-minute delivery "
    "stands out: it is 1.75 standard deviations above the mean, while every other value is within 0.7.",
]


def main() -> None:
    print(f"Goal: {GOAL}\n")
    log: list[str] = []
    answer = run_agent(get_llm(mock_responses=SCRIPT), GOAL, log=log)
    for i, entry in enumerate(log, 1):
        print(f"--- tool call {i}\n{entry}")
    print(f"--- answer\n{answer}")


if __name__ == "__main__":
    main()
