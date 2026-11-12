# 🧾 Cheatsheet

Every core idea in these notes on one page. Each row links to the page that explains it properly. New words? See the [Glossary](GLOSSARY.md).

📑 **On this page**

- [The core idea](#-the-core-idea)
- [The agent loop in 15 lines](#-the-agent-loop-in-15-lines)
- [Choosing how much autonomy](#-choosing-how-much-autonomy)
- [Patterns at a glance](#-patterns-at-a-glance)
- [Tools checklist](#-tools-checklist)
- [Memory and retrieval](#-memory-and-retrieval)
- [Stopping and error handling](#-stopping-and-error-handling)
- [Evaluation](#-evaluation)
- [Safety checklist](#-safety-checklist)
- [Production and cost](#-production-and-cost)

## 🧠 The core idea

> **An agent is an LLM that chooses an action, sees the result and chooses again, in a loop, until the goal is met.**

| Part | What it is | Read |
| --- | --- | --- |
| ① Model | The LLM that reads the context and decides the next step | [1.4](docs/01-foundations/01.4-how-llms-work.md) |
| ② Instructions | Role, goal, rules: the system prompt | [1.5](docs/01-foundations/01.5-anatomy-of-an-agent.md) |
| ③ Tools | Functions the model can *ask* your code to run | [3.1](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md) |
| ④ Memory | Short-term (this conversation) and long-term (stored between runs) | [5.1](docs/05-memory/05.1-short-term-vs-long-term-memory.md) |
| ⑤ Loop | Think → act → observe, with limits | [2.1](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md) |

**LLM facts every agent depends on** ([1.4](docs/01-foundations/01.4-how-llms-work.md)): the API is stateless (you resend the history every call); everything (instructions, history, tools, results and the reply) must fit in the context window; you pay per token; check the stop reason; outputs vary between runs.

## 🔁 The agent loop in 15 lines

```python
from common import tool_result, user

def run(llm, goal, tools, specs, system, max_steps=10):
    messages = [user(goal)]
    for _ in range(max_steps):                          # always cap the loop
        reply = llm.chat(messages, system=system, tools=specs)
        messages.append(reply.to_message())
        if reply.stop_reason == "max_tokens":
            return "Stopped: reply was cut off."        # don't run half-written tool calls
        if not reply.tool_calls:
            return reply.text                           # the model decided it is done
        for call in reply.tool_calls:                   # all results go back together
            try:
                messages.append(tool_result(call.id, tools[call.name](**call.arguments)))
            except Exception as exc:                    # errors are information, not crashes
                messages.append(tool_result(call.id, f"Error: {exc}", is_error=True))
    return "Stopped: step limit reached."
```

Build it step by step in [2.3](docs/02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md). Runnable: [`examples/01-anatomy-of-an-agent`](examples/01-anatomy-of-an-agent/README.md).

## 🎚 Choosing how much autonomy

| Level | Name | The model decides… | Use when |
| --- | --- | --- | --- |
| 0 | Single prompt | only the words | One step of language work |
| 1 | Fixed workflow | the words at each fixed step | Steps are known in advance |
| 2 | Router | which branch to take | Inputs fall into clear categories |
| 3 | Tool call | which function and arguments, once | One lookup or action per request |
| 4 | Agent loop | what to do next and when to stop | The path depends on what it finds |
| 5 | Autonomous | its own sub-goals, over a long time | Proven value, strong guardrails, human review |

**Rule:** pick the lowest level that solves the problem: code → one call → workflow → agent ([1.3](docs/01-foundations/01.3-the-autonomy-spectrum.md), [1.6](docs/01-foundations/01.6-when-not-to-use-an-agent.md)). Each step in a chain must be very reliable: 95% per step over 10 steps is only ~60% overall.

## 🧩 Patterns at a glance

| Pattern | Shape | Use when | Read |
| --- | --- | --- | --- |
| ReAct | Reason → act → observe, repeated | The general agent loop | [2.2](docs/02-the-agent-loop/02.2-react-explained.md) |
| Prompt chaining | Fixed sequence of calls, with checks between | A task splits cleanly into steps | [9.1](docs/09-agent-design-patterns/09.1-prompt-chaining.md) |
| Routing | Classify, then send to a specialist path | Distinct input types need different handling | [9.2](docs/09-agent-design-patterns/09.2-routing.md) |
| Parallelisation | Independent calls at once; combine (sectioning) or vote | Speed, or more confidence from several attempts | [9.3](docs/09-agent-design-patterns/09.3-parallelisation.md) |
| Orchestrator–workers | A lead model creates sub-tasks on the fly for workers | Sub-tasks can't be known in advance | [9.4](docs/09-agent-design-patterns/09.4-orchestrator-workers.md) |
| Evaluator–optimizer | Generate, grade against criteria, revise | Clear quality criteria; iteration helps | [8.2](docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md), [9.5](docs/09-agent-design-patterns/09.5-evaluator-optimizer.md) |
| Reflection | Draft → self-critique → revise | Cheap improvement; best with external signals | [8.1](docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md) |
| Self-critique with tests | Run real checks, feed failures back | Code or anything verifiable | [8.3](docs/08-reflection-and-self-correction/08.3-self-critique-with-tests.md) |
| Plan-and-execute | Write a plan, then run its steps | Long tasks that benefit from structure | [7.2](docs/07-planning-and-reasoning/07.2-plan-and-execute.md) |
| Human-in-the-loop | Pause for a person to approve or decide | Risky or irreversible actions | [9.6](docs/09-agent-design-patterns/09.6-human-in-the-loop.md) |
| Agentic RAG | Retrieval is a tool the agent calls when needed | Questions over your own documents | [6.4](docs/06-rag-for-agents/06.4-agentic-rag.md) |
| Supervisor | A manager agent delegates to specialist agents | Distinct skills or tool sets | [10.2](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md) |
| Handoffs | Agents pass control to each other | Conversation moves between domains | [10.3](docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md) |

Not sure? Use the decision flowchart in [9.7 Choosing a pattern](docs/09-agent-design-patterns/09.7-choosing-a-pattern.md).

## 🔧 Tools checklist

- [ ] **Clear name and description** saying what it does, when to use it and what it returns ([3.4](docs/03-tools-and-function-calling/03.4-designing-good-tools.md))
- [ ] **JSON Schema** with types, required fields, enums and a description per field ([3.2](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md))
- [ ] **Validate arguments** before running; return a helpful error the model can act on
- [ ] **Concise output**: high-signal results, truncated or paginated
- [ ] **Few tools**: each one costs context and adds a way to choose wrongly
- [ ] **Parallel calls**: run them concurrently; return all results in one message ([3.5](docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md))
- [ ] **Least privilege**: read-only by default; risky actions need approval ([13.3](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md))
- [ ] **Share across apps with MCP** when several hosts need the same tools ([4.1](docs/04-model-context-protocol/04.1-why-mcp-exists.md))

## 🗃 Memory and retrieval

| Need | Technique | Read |
| --- | --- | --- |
| Long conversation hits the context limit | Trim, summarise or compact older turns | [5.2](docs/05-memory/05.2-summarisation-and-context-compaction.md) |
| Recall past facts by meaning | Vector memory: embed, store, search by similarity | [5.3](docs/05-memory/05.3-vector-memory.md) |
| Different kinds of knowledge | Episodic (what happened), semantic (facts), procedural (how to) | [5.4](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md) |
| Answer from your documents | RAG: chunk → embed → retrieve → generate with citations | [6.1](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md) |
| Better retrieval quality | Good chunking, hybrid search, re-ranking; measure recall@k | [6.3](docs/06-rag-for-agents/06.3-chunking-strategies.md), [6.5](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md) |

## 🛑 Stopping and error handling

**Always stop on:** a final answer · a step limit · a time limit · a token or dollar budget · repeated identical calls · `max_tokens` truncation · a refusal ([2.4](docs/02-the-agent-loop/02.4-stopping-conditions.md), [16.5](docs/16-cost-and-performance/16.5-budget-limits-per-run.md)).

**Handle, don't crash** ([2.5](docs/02-the-agent-loop/02.5-handling-errors-in-the-loop.md)): tool exceptions → error result the model can read · invalid arguments → validation message · unknown tool → list the valid names · rate limits and server errors → retry with backoff · persistent failure → fall back or hand over to a person ([15.5](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)).

## 📏 Evaluation

| Measure | Question it answers | Read |
| --- | --- | --- |
| Task success | Did it reach the right final state or answer? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| Trajectory | Did it take a sensible path? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| Tool use | Right tools, right arguments, no wasted calls? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| LLM-as-judge | Quality where there's no exact answer (check the judge against human labels) | [12.3](docs/12-evaluation/12.3-llm-as-judge.md) |
| Cost and latency | Tokens, dollars and seconds per completed task | [16.1](docs/16-cost-and-performance/16.1-token-cost-maths.md) |

Build a dataset from real usage and edge cases ([12.4](docs/12-evaluation/12.4-building-an-eval-dataset.md)); run offline tests on every pull request and live evals on a schedule ([12.5](docs/12-evaluation/12.5-regression-testing-in-ci.md)).

## 🛡 Safety checklist

- [ ] Threat model written: what data, what actions, who could attack, through which inputs ([13.1](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md))
- [ ] Treat all tool results, web pages and documents as **untrusted**: they can carry prompt injections ([13.2](docs/13-safety-and-guardrails/13.2-prompt-injection.md))
- [ ] Avoid combining private data + untrusted content + a way to send data out in one agent
- [ ] Least-privilege credentials; sandbox code execution; restrict network access ([13.3](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md))
- [ ] Input and output guardrails: validation, PII checks, schema checks ([13.4](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md))
- [ ] Human approval for irreversible or high-impact actions ([13.5](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md))
- [ ] No secrets in prompts or logs; redact PII ([13.6](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md))

## 🚀 Production and cost

| Concern | Do this | Read |
| --- | --- | --- |
| See what happened | Trace every run: model calls and tool calls as spans | [14.1](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md) |
| Debug | Reproduce → read the trace → find the failing part → fix → add a test | [14.5](docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md) |
| Long tasks | Run in the background; poll or stream progress | [15.2](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md) |
| Retries | Idempotency keys on side-effecting tools | [15.3](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md) |
| Crashes | Checkpoint state after every step; resume | [15.4](docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md) |
| Cost | Cost ≈ Σ over steps of (input tokens × input price + output tokens × output price); input grows every step | [16.1](docs/16-cost-and-performance/16.1-token-cost-maths.md) |
| Repeated context | Prompt caching: stable prefix first (tools → system → history) | [16.2](docs/16-cost-and-performance/16.2-prompt-caching.md) |
| Easy vs hard requests | Route to smaller or larger models, or lower effort | [16.3](docs/16-cost-and-performance/16.3-model-routing.md) |
| Speed | Stream, parallelise tools, take fewer steps, cache | [16.4](docs/16-cost-and-performance/16.4-latency-optimisation.md) |

---

⬅️ **Back to:** [Home](README.md) · 📖 [Glossary](GLOSSARY.md) · 🗺 [Roadmap](ROADMAP.md)
