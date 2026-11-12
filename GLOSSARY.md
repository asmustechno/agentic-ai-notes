# 📖 Glossary

Every term used in these notes, A to Z. Each entry gives a short, plain definition and links to the page that explains it properly. Pages link here the first time they use a term.

> 🚧 This glossary grows as chapters are written. Missing a term? [Suggest it](.github/ISSUE_TEMPLATE/suggest-topic.md).

**Jump to:** [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [L](#l) · [M](#m) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [V](#v) · [W](#w)

## A

### Agent

A system in which a [large language model](#large-language-model-llm) decides, step by step, which actions to take (usually by calling [tools](#tool)) to reach a goal, and keeps going until the goal is met or it stops. → [1.1 What is an AI agent?](docs/01-foundations/01.1-what-is-an-ai-agent.md)

### Agent card

In A2A, a JSON document an agent publishes (usually at /.well-known/agent-card.json) describing its name, skills, endpoints, capabilities and authentication requirements. → [10.5 Agent-to-agent protocols](docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md)

### Agent loop

The repeating cycle at the heart of an agent: observe the current state, think about what to do, act (for example by calling a tool), then observe the result. → [2.1 The observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

### Agent-computer interface (ACI)

The set of commands and tools an agent uses to work in a computer environment, such as search, view and edit commands for a coding agent. Its design strongly affects how well the agent performs. → [17.1 Coding agent](docs/17-case-studies/17.1-coding-agent.md)

### Agent2Agent protocol (A2A)

An open protocol, under the Linux Foundation, that lets independent agents discover each other through Agent Cards, exchange messages and track shared tasks without exposing their internals. → [10.5 Agent-to-agent protocols](docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md)

### API key

A secret string that identifies you to a model provider and lets your code call its API. Keep it in a `.env` file, never in code. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Approval gate

Code in the agent loop that pauses a risky tool call, shows a person a preview of exactly what will happen, and runs it only if they approve. → [13.5 Human approval for risky actions](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md)

### At-least-once delivery

A queue guarantee that every job is delivered until a worker confirms it, so nothing is lost but some jobs are processed more than once. Handlers must therefore be safe to run twice. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Audit log

An append-only record of every action an agent took or was refused, with who approved it and what happened, kept for investigation and accountability. → [13.5 Human approval for risky actions](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md)

### Autonomy spectrum

A scale describing how much an LLM system's model decides, from a single prompt (code decides everything) to a fully autonomous agent (the model sets its own sub-goals). → [1.3 The autonomy spectrum](docs/01-foundations/01.3-the-autonomy-spectrum.md)

## B

### Background agent

An agent run that no one is waiting for in real time: it is started by a schedule or an event and reports its result somewhere useful, such as a ticket or a chat message. → [15.2 Sync vs async & background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Benchmark

A public, standardised set of tasks with a fixed way of grading them, used to compare models or agent systems. A score describes the whole system tested (model plus scaffold), on that benchmark's tasks only. → [12.6 Public benchmarks (overview)](docs/12-evaluation/12.6-public-benchmarks.md)

### Blackboard

A shared store that several agents read and write through tools. It needs rules for who may see and change what, and for catching conflicting writes. → [10.4 Shared state & communication](docs/10-multi-agent-systems/10.4-shared-state-and-communication.md)

### Browser agent

An agent that uses a web browser through tools, such as opening pages, reading their text and clicking or filling elements, to complete tasks on websites. → [3.7 Computer use & browser agents](docs/03-tools-and-function-calling/03.7-computer-use-and-browser-agents.md)

## C

### Canary token

A unique, meaningless string planted in a system prompt or secret document. If it ever appears in a model's output, you know the hidden text has leaked, so an output guardrail can block the reply. → [18.5 Project 5: Production-ready support agent](docs/18-projects/18.5-project-5-production-support-agent.md)

### Chatbot

A system that answers with a single model reply per message and takes no actions. It can only use what the model already knows or what is in the prompt. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

### Checkpoint

A saved snapshot of a run's state (for an agent, the messages and the step counter) that lets the run resume after a crash instead of starting over. → [15.4 State persistence & resumability](docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md)

### Circuit breaker

A guard that stops calling a dependency after repeated failures, fails fast for a cool-down period, then lets one trial call through to see whether it has recovered. → [15.5 Rate limits & fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Compounding errors

The way small per-step error rates add up over many steps: if each step is right with probability p, all n steps are right with probability pⁿ. A key reason long agent runs need ways to catch mistakes. → [1.6 When NOT to use an agent](docs/01-foundations/01.6-when-not-to-use-an-agent.md)

### Computer use

Letting a model operate a computer like a person: it receives screenshots and asks for mouse and keyboard actions, which your code performs on an isolated machine. → [3.7 Computer use & browser agents](docs/03-tools-and-function-calling/03.7-computer-use-and-browser-agents.md)

### Confused deputy

An attack in which a program with legitimate authority, such as an MCP proxy server holding OAuth credentials, is tricked into using that authority on an attacker's behalf. → [4.6 Security for MCP servers](docs/04-model-context-protocol/04.6-mcp-security.md)

### Container

A running instance of a container image: an isolated process with its own filesystem, started the same way on any machine. → [15.6 Deploying with FastAPI & Docker](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Container image

A packaged, read-only bundle of an application with its runtime and dependencies (for example a Docker image), built once and run anywhere. It should never contain secrets. → [15.6 Deploying with FastAPI & Docker](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Context isolation

Giving a sub-task its own fresh context, so its raw work (searches, files, tool output) stays out of the main agent's context and only a short result comes back. → [10.1 Why multiple agents?](docs/10-multi-agent-systems/10.1-why-multiple-agents.md)

### Context window

The maximum amount of text, measured in [tokens](#token), that a model can read in one request. Everything the model "knows" about the current task must fit inside it. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Correlation ID

An identifier, such as a run ID, attached to every log line and trace of one request or agent run, so all its records can be found and joined together. → [14.2 Logging tool calls](docs/14-observability-and-debugging/14.2-logging-tool-calls.md)

## D

### Data contamination

When benchmark or test questions (or their answers) end up in a model's training data, so its score partly reflects memorisation and overstates how well it handles new problems. → [12.6 Public benchmarks (overview)](docs/12-evaluation/12.6-public-benchmarks.md)

### Data exfiltration

Getting private data out of a system to somewhere an attacker can read it, for example by tricking an agent into emailing it or putting it in a URL. → [13.1 Threat model for agents](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Dead-letter queue (DLQ)

A holding queue for jobs that failed permanently or ran out of retries, so they are neither retried forever nor silently dropped, and a human can inspect and replay them. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Defence in depth

Stacking several independent, imperfect safety layers so that an attack that gets past one is caught by another. → [13.1 Threat model for agents](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Dual LLM pattern

A design in which a privileged model plans and calls tools but never reads untrusted text, while a quarantined model with no tools reads it; code passes results between them only as variable references. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## E

### Embedding

A list of numbers that represents the meaning of a piece of text. Texts with similar meanings have embeddings that are close together, which makes search by meaning possible. → [6.2 Embeddings & vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### Environment variable

A named setting passed to a program by its environment rather than written in its code, such as `LLM_PROVIDER=mock`. The examples read them from a `.env` file. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Eval

Short for evaluation: a repeatable test that measures how well an LLM system performs on a set of example tasks. → [12.1 Why evals are hard for agents](docs/12-evaluation/12.1-why-agent-evals-are-hard.md)

### Evaluator-optimizer

A loop in which one LLM call generates a result and a separate evaluator grades it against clear criteria and gives feedback; the generator revises until the result passes or a round limit is reached. → [8.2 The evaluator–optimizer loop](docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md)

### Exponential backoff

A retry strategy that doubles the wait after each failure (for example 0.5 s, 1 s, 2 s, 4 s) up to a cap, giving a struggling service time to recover. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

## F

### Function calling

The model's ability to reply with a structured request to run one of the tools you described, instead of (or as well as) plain text. Your code runs the tool and sends the result back. Also called *tool calling* or *tool use*. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

## G

### Gate

A check in plain code between two steps of a workflow, such as "is this valid JSON?" or "is it under 80 words?". If it fails, the workflow stops or retries that step instead of passing bad output on. → [9.1 Prompt chaining](docs/09-agent-design-patterns/09.1-prompt-chaining.md)

### Guardrail

A check that runs before or after a model call to block, fix or flag unsafe or invalid input and output. → [13.4 Input & output guardrails](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md)

## H

### Hallucination

When a model states something false or invented as if it were true, such as a delivery date it had no data for. Giving the model real data through tools or retrieval reduces it. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

### Handoff

Passing control of a conversation from one agent to another, which then answers the user directly with its own instructions and tools. Usually offered to the model as a tool such as transfer_to_billing. → [10.3 Peer-to-peer & handoffs](docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md)

### Health check

A cheap endpoint, such as GET /healthz, that a load balancer or orchestrator calls to decide whether a service instance is alive and should receive traffic. → [15.6 Deploying with FastAPI & Docker](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Human-in-the-loop (HITL)

A design in which an agent pauses at chosen points so a person can approve, edit or reject an action, or take over the case, before the run continues. → [9.6 Human-in-the-loop](docs/09-agent-design-patterns/09.6-human-in-the-loop.md)

## I

### Idempotency key

A unique id sent with a request that has a side effect, so the receiver can recognise a retry of the same request and return the first result instead of acting twice. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Idempotent

Describes an operation that has the same effect whether it runs once or many times, like setting a thermostat to 21°C. Idempotent operations are safe to retry. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Indirect prompt injection

Prompt injection that arrives through content the agent reads, such as a web page, email, document or tool result, rather than from the user. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

### Instructions

The part of an agent that tells the model its role, goal, rules and how to use its tools, usually written as the system prompt. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## J

### Jitter

Randomness added to retry waits so that many clients that failed at the same moment do not all retry at the same moment. → [15.3 Queues, retries & idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Job queue

A buffer between the part of a system that accepts work and the workers that do it. It absorbs bursts and keeps jobs safe if a worker crashes. → [15.1 Architecture of a production agent](docs/15-production-and-deployment/15.1-production-architecture.md)

### JSON Schema

A standard way to describe the shape of JSON data: which fields exist, their types, which are required and which values are allowed. Tool definitions use it to describe a tool's inputs. → [3.2 JSON Schema for tool definitions](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md)

### JSON-RPC

A simple message format for remote procedure calls written in JSON: each request has an id, a method and params, and each response carries the same id with a result or an error. MCP messages use JSON-RPC 2.0. → [4.2 Hosts, clients and servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

## L

### Large language model (LLM)

A neural network trained on large amounts of text to predict the next [token](#token). Given a prompt, it generates text one token at a time. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Least privilege

Giving each part of a system, including an agent and its tools, only the access it needs for its task, for only as long as it needs it. → [13.3 Least-privilege tools & sandboxing](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md)

### Lethal trifecta

Simon Willison's name for an agent that combines access to private data, exposure to untrusted content and a way to communicate externally; together they let an attacker steal data. Removing any one leg removes that attack. → [13.1 Threat model for agents](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### LLM-as-judge

Using a language model to grade another model's or agent's output against a rubric, returning a structured verdict. It needs checking against human labels before you trust it. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

### Long-term memory

Information an agent keeps between runs, such as user preferences, past results or documents. Code stores it and puts relevant parts back into the context when needed. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## M

### Max tokens

The limit you set on how many tokens the model may write in one reply. If it is reached, the reply is cut off and the stop reason says so. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### MCP client

The connector inside an MCP host that talks to exactly one MCP server, sending it requests such as tools/list and tools/call. → [4.2 Hosts, clients and servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### MCP host

The AI application that uses MCP servers, such as a desktop chat app, an IDE or your own agent. It runs one MCP client per server, works with the model and enforces user consent. → [4.2 Hosts, clients and servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### MCP prompt

A reusable message template offered by an MCP server, which the user chooses, often as a slash command. One of the three server primitives, alongside tools and resources. → [4.3 Tools, resources and prompts](docs/04-model-context-protocol/04.3-tools-resources-and-prompts.md)

### MCP resource

Read-only data offered by an MCP server and identified by a URI, such as a file or a database schema. The host application decides when to attach it to the model's context. → [4.3 Tools, resources and prompts](docs/04-model-context-protocol/04.3-tools-resources-and-prompts.md)

### MCP server

A program that exposes tools, resources and prompts from one system (such as GitHub, a database or your notes) through the Model Context Protocol, so any MCP host can use them. → [4.4 Build a simple MCP server](docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md)

### MockLLM

A fake model used in these notes' examples. It returns pre-written responses, so every example and test can run offline, for free, and with the same result every time. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Model cascade

A routing strategy that tries a cheaper model first, checks its answer, and sends the request to a more capable model only if the check fails. → [16.3 Model routing](docs/16-cost-and-performance/16.3-model-routing.md)

### Model Context Protocol (MCP)

An open protocol that standardises how applications give models access to tools, data and prompts, so one integration works across many apps. → [4.1 Why MCP exists](docs/04-model-context-protocol/04.1-why-mcp-exists.md)

### Model fallback

Switching a request to another model or provider when the first one is unavailable, overloaded or declines it. → [15.5 Rate limits & fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Model gateway

The single component every model call goes through. It handles retries, rate limits, fallbacks between models or providers, and records tokens and cost. → [15.1 Architecture of a production agent](docs/15-production-and-deployment/15.1-production-architecture.md)

### Model routing

Choosing which model handles each request, for example sending easy work to a small, cheap model and hard work to a large one, using rules, a classifier or a cascade. → [16.3 Model routing](docs/16-cost-and-performance/16.3-model-routing.md)

### Multi-agent system

A system in which several agents, each with its own instructions, tools and context, work on one task by delegating to or handing over to each other. → [10.1 Why multiple agents?](docs/10-multi-agent-systems/10.1-why-multiple-agents.md)

## O

### Observability

Being able to answer "what happened, and why?" about a running system from the data it records (traces, logs and metrics), without adding new code first. → [14.1 Tracing agent runs](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### Observation

The result an agent sees after an action, such as a tool's output or error, added to the conversation so the model can use it in its next decision. In ReAct it is the line your code writes after each Action. → [2.1 The observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

### OpenTelemetry (OTel)

An open, vendor-neutral standard and set of libraries for creating and exporting traces, metrics and logs, so the same instrumentation works with many backends. → [14.3 OpenTelemetry for LLM apps](docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md)

### Orchestrator-workers

A pattern in which a lead LLM call breaks a task into sub-tasks decided at run time, worker calls handle one sub-task each, and the lead combines their results. → [9.4 Orchestrator–workers](docs/09-agent-design-patterns/09.4-orchestrator-workers.md)

## P

### Parallel tool calls

Several tool calls returned by the model in a single turn. Your code may run them at the same time, but must return one result per call, matched by ID. → [3.5 Parallel tool calls](docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md)

### Parallelisation

Running independent LLM calls at the same time and combining the results in code: either different subtasks (sectioning) or the same task several times, aggregated by a vote (voting). → [9.3 Parallelisation (sectioning & voting)](docs/09-agent-design-patterns/09.3-parallelisation.md)

### pass@k (pass at k)

The chance that at least one of k independent attempts at a task succeeds. It rises towards 1 as k grows, and suits tasks where you can automatically pick the attempt that worked. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### pass^k (pass hat k)

The chance that all k independent attempts at a task succeed. It falls as k grows, and measures the consistency that customer-facing agents need. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Personally identifiable information (PII)

Information that can identify a person, such as a name, email address, phone number, card number or ID number. → [13.6 Secrets & PII handling](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md)

### Position bias

A judge model's tendency to prefer an answer because of where it appears (for example, first) rather than what it says. Countered by asking twice with the order swapped. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

### Prompt caching

A provider feature that reuses the work already done on the unchanged beginning (prefix) of a request, making repeated input tokens much cheaper and faster to process. → [16.2 Prompt caching](docs/16-cost-and-performance/16.2-prompt-caching.md)

### Prompt chaining

A workflow that splits a task into a fixed sequence of LLM calls, each working on the previous call's output, usually with gates in code between the steps. → [9.1 Prompt chaining](docs/09-agent-design-patterns/09.1-prompt-chaining.md)

### Prompt injection

An attack in which text the model reads, such as a user message, a web page or a tool result, contains instructions designed to override the developer's instructions. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## R

### Rate limit

A cap a provider puts on how much you can send in a time window, such as requests or tokens per minute. Going over it returns HTTP 429. → [15.5 Rate limits & fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### ReAct

Short for "Reasoning and Acting": a pattern in which the model alternates between writing a reasoning step and taking an action, then reads the observation before continuing. Introduced by Yao et al. (2022). → [2.2 ReAct explained](docs/02-the-agent-loop/02.2-react-explained.md)

### Redaction

Replacing sensitive values in text with placeholders or masks, for example turning an email address into <EMAIL_1>, before the text reaches a model or a log. → [13.6 Secrets & PII handling](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md)

### Reflection

A pattern in which a model drafts an answer, critiques the draft (usually with a separate critic prompt and a checklist), and revises it, repeating until the critique finds no problems or a round limit is hit. → [8.1 The reflection pattern](docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md)

### Regression test

A test that captures a bug that was fixed, such as a recorded failing agent run, so the bug is caught automatically if it ever comes back. → [14.5 Debugging a broken agent](docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md)

### Retrieval-augmented generation (RAG)

A technique that first retrieves relevant documents, then gives them to the model along with the question, so the answer is grounded in that information. → [6.1 RAG in 5 minutes](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md)

### Routing

A workflow that first classifies an input, checks the label, and then sends the input to a handler (prompt, tools or model) specialised for that kind of input. → [9.2 Routing](docs/09-agent-design-patterns/09.2-routing.md)

### Rubric

A written list of criteria, each with a clear pass/fail rule, that a human or model grader uses so that grading is consistent. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

### Rug pull

When an MCP server changes its tool definitions or behaviour after a user has approved it, for example by adding hidden instructions to a description. Pinning tool definitions defends against it. → [4.6 Security for MCP servers](docs/04-model-context-protocol/04.6-mcp-security.md)

### Run budget

Limits on how many steps, tokens, dollars and seconds one agent run may use, checked in the loop before each model call so the run stops gracefully when a limit is reached. → [16.5 Budget limits per run](docs/16-cost-and-performance/16.5-budget-limits-per-run.md)

## S

### Sampling

How a model picks each next token from its predicted probabilities, rather than always taking the most likely one. It is why the same prompt can give different replies. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Sandbox

An isolated, disposable environment, such as a locked-down container or microVM, where an agent's code runs with limited files, network and resources and no secrets. → [13.3 Least-privilege tools & sandboxing](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md)

### Self-correction

A model revising its own output. Intrinsic self-correction uses only what the model already knows and is unreliable for reasoning; self-correction with external feedback (tests, errors, tool results) works much better. → [8.4 Limits of self-correction](docs/08-reflection-and-self-correction/08.4-limits-of-self-correction.md)

### Semantic conventions

Agreed names and meanings for span names and attributes in OpenTelemetry, such as gen_ai.usage.input_tokens, so that every backend can read data from any instrumented app. → [14.3 OpenTelemetry for LLM apps](docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md)

### Server tool

A tool the model provider runs on its own infrastructure inside the API call, such as web search or code execution, so your code does not execute it. → [3.6 Code execution as a tool](docs/03-tools-and-function-calling/03.6-code-execution-as-a-tool.md)

### Server-sent events (SSE)

A simple HTTP standard for a server to push a stream of events to a client over one long-lived response, often used to stream an agent's progress to a browser. → [15.2 Sync vs async & background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Short-term memory

What an agent knows during the current run: the conversation so far, including every tool call and result. It lives in the context window. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

### Span

One timed step inside a trace, such as a model call or a tool call, with a name, start and end time, attributes, a status and a link to its parent step. → [14.1 Tracing agent runs](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### Stateless

Describes an API that keeps no memory between calls. LLM APIs are stateless, so your code must resend the conversation every time. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### stdio transport

The MCP transport in which the host starts the server as a local subprocess and they exchange newline-delimited JSON-RPC messages over its standard input and output. → [4.2 Hosts, clients and servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### Stop reason

The field in a model's reply that says why it stopped writing: it finished, it wants to call a tool, it hit the output limit, or it refused. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Stopping condition

A rule that ends an agent run: the good one is a complete final answer; the safety ones are limits your code enforces, such as maximum steps, time, tokens, cost or repeated identical calls. → [2.4 Stopping conditions](docs/02-the-agent-loop/02.4-stopping-conditions.md)

### Streamable HTTP

The MCP transport for servers that run independently, often remotely: the client sends each message as an HTTP POST to one endpoint, and the reply comes back as JSON or as a stream of events for that request. → [4.2 Hosts, clients and servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### Streaming

Receiving a model's reply piece by piece as it is generated, instead of all at once at the end, so users see the first words sooner. → [16.4 Latency optimisation](docs/16-cost-and-performance/16.4-latency-optimisation.md)

### Strict mode

A tool option (`strict: true`) that makes the provider constrain the model's output so its tool arguments always match the JSON Schema. Anthropic and OpenAI both offer it, with slightly different schema rules. → [3.2 JSON Schema for tool definitions](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md)

### Structured logging

Writing each log entry as data (usually one JSON object with named fields) instead of a free-text sentence, so logs can be searched, filtered and counted. → [14.2 Logging tool calls](docs/14-observability-and-debugging/14.2-logging-tool-calls.md)

### Subagent

An agent started by another agent to do one focused sub-task in its own context. It receives a brief and returns only its final result. → [10.2 Supervisor & hierarchical](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md)

### Supervisor agent

An agent that keeps control of a task, delegates parts of it to specialist agents (usually exposed to it as tools) and combines their results. Also called a lead, orchestrator or manager agent. → [10.2 Supervisor & hierarchical](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md)

### Sycophancy

A model's tendency to agree with the user, or with what the prompt implies, even when that means giving up a correct answer. It is why "are you sure?" is a poor way to check an answer. → [8.4 Limits of self-correction](docs/08-reflection-and-self-correction/08.4-limits-of-self-correction.md)

### System prompt

Instructions given to the model separately from the user's messages, used to set its role, rules and behaviour for the whole conversation. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## T

### Taint tracking

Remembering when untrusted content has entered an agent's context, and restricting risky actions (such as sending data out) from that point on. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

### Temperature

A sampling setting that controls how random a model's output is: lower is more predictable, higher is more varied. Several recent models no longer accept it, and even at 0 outputs can vary. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Text-to-SQL

Turning a question in plain language into a SQL query that answers it. Usually evaluated by comparing the query's results with those of a reference query. → [17.4 Data analysis agent](docs/17-case-studies/17.4-data-analysis-agent.md)

### Threat model

A written answer to four questions about a system: what is valuable, who might attack it, how they could get in, and what damage they could do. → [13.1 Threat model for agents](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Time to first token (TTFT)

How long after a request is sent the first token of the response arrives. It grows with the amount of uncached input the model has to read. → [16.4 Latency optimisation](docs/16-cost-and-performance/16.4-latency-optimisation.md)

### Token

The unit of text a model reads and writes: often a word, part of a word, or a punctuation mark. Context windows, limits and prices are all measured in tokens. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Token bucket

A rate-limiting algorithm: tokens refill at a steady rate up to a maximum, each request takes one, and requests wait when the bucket is empty. It allows short bursts while capping the average rate. → [15.5 Rate limits & fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Token passthrough

An anti-pattern in which an MCP server accepts an access token that was not issued for it and forwards it to another API. The MCP authorization specification forbids it. → [4.6 Security for MCP servers](docs/04-model-context-protocol/04.6-mcp-security.md)

### Tokenizer

The component that splits text into tokens before the model reads it. Each provider has its own, so the same text gives different token counts on different models. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Tool

A function that your code exposes to the model, described by a name, a description and an input schema. The model can ask for it to be run; your code runs it and returns the result. → [3.1 What is a tool?](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md)

### Tool call

The model's structured request to run one tool: the tool's name, its arguments and an ID. Your code runs it and replies with a tool result carrying the same ID. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Tool choice

A request setting that controls whether the model may call a tool, must call one, must call a specific one, or may not call any on this turn. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Tool poisoning

An attack that hides instructions for the model inside a tool's name, description or schema, so that simply connecting the tool can steer the agent, for example into leaking files. → [4.6 Security for MCP servers](docs/04-model-context-protocol/04.6-mcp-security.md)

### Tool result

The message your code sends back after running a tool call, linked to it by ID. It carries the tool's output, or an error message the model can read and act on. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Trace

The record of one request or agent run as a tree of spans that share one trace ID: the run at the root, with model calls and tool calls as its children. → [14.1 Tracing agent runs](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### Trajectory

The ordered list of steps an agent took in one run, especially its tool calls and their arguments. Evals compare it with an expected trajectory to check the path, not just the result. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Transformer

The neural network architecture behind modern LLMs, introduced in 2017. It lets each token take every earlier token into account when predicting the next one. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## V

### Virtual environment

A self-contained folder of Python packages for one project, so its dependencies do not clash with other projects. Created with `python -m venv .venv`. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

## W

### Webhook

An HTTP request a system sends to a URL you registered when something happens, such as an agent run finishing, so you don't have to poll. → [15.2 Sync vs async & background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Workflow

An LLM system in which your code fixes the sequence of steps in advance and the model fills in parts, such as writing text or classifying input. Contrast with an agent, where the model chooses the steps. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)
