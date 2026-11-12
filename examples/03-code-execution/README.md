# 03 · Code execution as a tool

The model writes a Python script; a `run_python` tool runs it in a separate process with a timeout, output limits, no inherited environment variables, an empty temporary folder, and (on Linux and macOS) memory, CPU and file limits. The model reads the result, including any traceback, and fixes its own bug. Used in [3.6 Code execution as a tool](../../docs/03-tools-and-function-calling/03.6-code-execution-as-a-tool.md).

> **A subprocess is not a security sandbox.** The code still runs as your user, with access to your files and your network. This example is for learning and for code you would run yourself. For untrusted input, use real isolation: a container with no network, [gVisor](https://gvisor.dev/), a [Firecracker](https://firecracker-microvm.github.io/) microVM, or a hosted sandbox such as Anthropic's code execution tool or OpenAI's Code Interpreter. See the page for details.

## Run it

```bash
cd examples
python 03-code-execution/main.py
```

Output (offline; the model is `MockLLM`, but the code really runs):

```text
Goal: Delivery times this week were 12, 15, 11, 30 and 14 minutes. What are the mean and standard deviation, and is any value an outlier?

--- tool call 1
code:
import statistics as st
times = [12, 15, 11, 30, 14]
print(st.mean(times), st.stdev(times))
print(stats.median(times))

result:
[exit code 1]
stdout:
16.4 7.765307463326871

stderr:
Traceback (most recent call last):
  File "snippet.py", line 4, in <module>
    print(stats.median(times))
          ^^^^^
NameError: name 'stats' is not defined

--- tool call 2
code:
import statistics as st
times = [12, 15, 11, 30, 14]
mean, sd = st.mean(times), st.stdev(times)
print(f"mean={mean:.1f} sd={sd:.2f}")
print("z-scores:", {t: round((t - mean) / sd, 2) for t in times})

result:
[exit code 0]
stdout:
mean=16.4 sd=7.77
z-scores: {12: -0.57, 15: -0.18, 11: -0.7, 30: 1.75, 14: -0.31}

--- answer
The mean is 16.4 minutes and the standard deviation is about 7.77 minutes. The 30-minute delivery stands out: it is 1.75 standard deviations above the mean, while every other value is within 0.7.
```

## Test it

```bash
pytest 03-code-execution
```

Every snippet in the tests is harmless: arithmetic, a deliberate `1 / 0`, an infinite loop that the timeout kills after one second, and a large `print`. The memory-limit test runs only on Linux and macOS.

## Things to try

- Run `run_python("import time; time.sleep(10)", timeout=2)`. What does the model receive?
- Print a 1 MB string. What reaches the model?
- List three things a malicious script could still do with this runner. (The page has answers.)
