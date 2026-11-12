🏠 [Home](../../README.md) › 15 · Production & Deployment

# 15 · Production & Deployment

> **Estimated reading time:** ~69 min · **Difficulty:** 🔴 Advanced · **Prerequisites:** [02 · The Agent Loop](../02-the-agent-loop/README.md), [14 · Observability & Debugging](../14-observability-and-debugging/README.md)

A working agent on your laptop is the easy half. This chapter covers the other half: what has to surround the agent loop so that it keeps working when many users arrive at once, a provider is overloaded, a deploy kills a run half-way through, or a retry tries to send the same email twice. You will see the architecture of a production agent, choose between synchronous and background runs, make retries safe with idempotency keys, checkpoint runs so they resume after a crash, survive rate limits and outages with fallbacks and circuit breakers, and finally ship the agent as a tested FastAPI service in a Docker container.

## 🎯 What you'll learn

- The components around the loop (API layer, job queue, workers, state store, model gateway, guardrails, observability, evals) and when you need each
- When to answer inside one request, when to stream, and when to return a run id and work in the background
- Which errors to retry, how to back off with jitter, and how idempotency keys and dead-letter queues prevent duplicate side effects
- How to checkpoint an agent run in SQLite and resume it after a crash without repeating work
- How to handle rate limits, fall back to another model or provider, and use a circuit breaker; and what Anthropic's server-side refusal fallback does and doesn't do
- How to serve an agent with FastAPI, test it with `TestClient` and `MockLLM`, and package it in a secure Docker image

## 📋 Prerequisites

- [2.3 A 50-line agent from scratch](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md) and [2.5 Handling errors in the loop](../02-the-agent-loop/02.5-handling-errors-in-the-loop.md): the loop this chapter wraps
- [14.1 Tracing agent runs](../14-observability-and-debugging/14.1-tracing-agent-runs.md): helpful for the observability parts
- Basic HTTP (status codes, headers) and some familiarity with the command line. Docker is optional: every example runs and tests without it

## 👀 Chapter overview

![Architecture of a production agent: a client calls an API layer, which answers short tasks directly or queues long ones. Workers run the agent loop, call models through a gateway with primary and fallback providers, call tool services, and checkpoint each step to a state store. Guardrails check the loop; observability and evals cover everything.](../../assets/diagrams/15-production-architecture.svg)

*The agent loop is the small box in the middle. Page 15.1 explains the whole picture; 15.2 covers the API layer's sync-or-async choice; 15.3 the queue and safe retries; 15.4 the state store; 15.5 the model gateway; 15.6 packages the service for deployment.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 15.1 | [Architecture of a production agent](./15.1-production-architecture.md) — The components around the loop that make it reliable. | 🔴 Advanced | ~12 min |
| 15.2 | [Sync vs async & background agents](./15.2-sync-vs-async-agents.md) — Request-response agents versus long-running jobs. | 🔴 Advanced | ~10 min |
| 15.3 | [Queues, retries & idempotency](./15.3-queues-retries-and-idempotency.md) — Retry safely without doing things twice. | 🔴 Advanced | ~12 min |
| 15.4 | [State persistence & resumability](./15.4-state-persistence-and-resumability.md) — Save progress so a run can resume after a crash. | 🔴 Advanced | ~10 min |
| 15.5 | [Rate limits & fallbacks](./15.5-rate-limits-and-fallbacks.md) — Stay up when a provider is slow, busy or down. | 🔴 Advanced | ~10 min |
| 15.6 | [Deploying with FastAPI & Docker](./15.6-deploying-with-fastapi-and-docker.md) — Ship an agent as a containerised web service. | 🔴 Advanced | ~15 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

| Example | What it shows | Used in |
| --- | --- | --- |
| [`15-retries-idempotency`](../../examples/15-retries-idempotency/README.md) | Which errors to retry, backoff with jitter, idempotency keys, an at-least-once queue with a dead-letter queue | [15.3](./15.3-queues-retries-and-idempotency.md), [15.1](./15.1-production-architecture.md) |
| [`15-resumable-agent`](../../examples/15-resumable-agent/README.md) | Checkpointing every step in SQLite; resuming after simulated crashes without repeating side effects | [15.4](./15.4-state-persistence-and-resumability.md), [15.1](./15.1-production-architecture.md) |
| [`15-fallbacks`](../../examples/15-fallbacks/README.md) | A token bucket, a circuit breaker and a provider fallback chain, driven by a fake clock | [15.5](./15.5-rate-limits-and-fallbacks.md), [15.1](./15.1-production-architecture.md) |
| [`15-fastapi-service`](../../examples/15-fastapi-service/README.md) | A FastAPI agent service (sync and background runs, health check, env config, JSON logs) with a Dockerfile and Compose file | [15.6](./15.6-deploying-with-fastapi-and-docker.md), [15.2](./15.2-sync-vs-async-agents.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [14 · Observability & Debugging](../14-observability-and-debugging/README.md) ·
▶️ **Start reading:** [15.1 Architecture of a production agent](./15.1-production-architecture.md) ·
➡️ **Next chapter:** [16 · Cost & Performance](../16-cost-and-performance/README.md)
