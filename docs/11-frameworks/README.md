🏠 [Home](../../README.md) › 11 · Frameworks

# 11 · Frameworks

> **Estimated reading time:** ~113 min · **Difficulty:** 🟡 Intermediate · **Prerequisites:** [01 · Foundations](../01-foundations/README.md), [02 · The Agent Loop](../02-the-agent-loop/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md)

There are now more agent frameworks than anyone can try. This chapter gives you a map, then rebuilds **the same agent** (the Paris-vs-Rome weather agent from [1.5](../01-foundations/01.5-anatomy-of-an-agent.md)) in LangGraph, CrewAI, Microsoft Agent Framework (and the archived AutoGen), the OpenAI Agents SDK, the Claude Agent SDK, LlamaIndex and Pydantic AI, so you can compare like with like. It ends with the case for using no framework at all, and a short process for choosing. Every example runs offline with that framework's own fake model, and every page states the exact package version it was checked against.

## 🎯 What you'll learn

- How each framework names and packages the five parts of an agent: model, instructions, tools, memory and loop
- The core abstraction of each framework: state graphs, crews, agents and workflows, runners and handoffs, a harness, query-engine tools, typed outputs
- The current status of Microsoft AutoGen (archived) and its successor, Microsoft Agent Framework
- How the Claude Agent SDK (a full agent harness) differs from the Anthropic SDK's tool runner
- How to test agents offline in each framework with its fake or scripted model
- When a plain loop over the provider SDK beats any framework
- A question-driven way to choose, and how to keep your options open

## 📋 Prerequisites

- [1.5 Anatomy of an agent](../01-foundations/01.5-anatomy-of-an-agent.md): the five parts every framework packages
- [2.3 A 50-line agent from scratch](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md): the loop the frameworks hide
- [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md): what happens when a model calls a tool
- Helpful for some pages: [4.1 Why MCP exists](../04-model-context-protocol/04.1-why-mcp-exists.md) (Claude Agent SDK), [6.1 RAG in 5 minutes](../06-rag-for-agents/06.1-rag-in-5-minutes.md) (LlamaIndex), [10.1 Why multiple agents?](../10-multi-agent-systems/10.1-why-multiple-agents.md) (CrewAI, handoffs, workflows)
- Python 3.11 and the ability to create a [virtual environment](../../GLOSSARY.md#virtual-environment) per example

## 👀 Chapter overview

![Four layers of agent tooling, bottom to top. Your own loop over a provider SDK, or the Anthropic SDK tool runner. Agent SDKs that run the loop for you: OpenAI Agents SDK, Pydantic AI, LlamaIndex agents, Microsoft Agent Framework. Orchestration frameworks where you design the control flow: LangGraph, CrewAI, Agent Framework workflows, LlamaIndex workflows. Harnesses with built-in tools and permissions: Claude Agent SDK, LangChain Deep Agents, the Agent Framework harness agent.](../../assets/diagrams/11-framework-layers.svg)

*The chapter walks this picture. 11.1 maps it, 11.2–11.8 visit each framework with the same example, 11.9 covers the bottom layer, and 11.10 helps you decide how high to climb.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 11.1 | [Framework landscape](./11.1-framework-landscape.md) — A comparison table of the main agent frameworks. | 🟢 Beginner | ~8 min |
| 11.2 | [LangGraph](./11.2-langgraph.md) — Agents as graphs of nodes and edges with explicit state. | 🟡 Intermediate | ~15 min |
| 11.3 | [CrewAI](./11.3-crewai.md) — Role-based crews of agents working on tasks. | 🟡 Intermediate | ~12 min |
| 11.4 | [Microsoft AutoGen & Agent Framework](./11.4-microsoft-autogen-and-agent-framework.md) — Microsoft's multi-agent frameworks. | 🟡 Intermediate | ~12 min |
| 11.5 | [OpenAI Agents SDK](./11.5-openai-agents-sdk.md) — Agents, handoffs and guardrails from OpenAI. | 🟡 Intermediate | ~12 min |
| 11.6 | [Claude Agent SDK](./11.6-claude-agent-sdk.md) — The Claude Code agent harness as a library. | 🟡 Intermediate | ~12 min |
| 11.7 | [LlamaIndex agents](./11.7-llamaindex-agents.md) — Agents built around data and retrieval. | 🟡 Intermediate | ~12 min |
| 11.8 | [Pydantic AI](./11.8-pydantic-ai.md) — Type-safe agents with validated inputs and outputs. | 🟡 Intermediate | ~12 min |
| 11.9 | [The no-framework approach](./11.9-the-no-framework-approach.md) — When a plain loop over the provider SDK is the best choice. | 🟡 Intermediate | ~10 min |
| 11.10 | [How to choose a framework](./11.10-how-to-choose.md) — Questions that point you to the right tool. | 🟢 Beginner | ~8 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

Each framework example has its own `requirements.txt` and needs its own virtual environment; see each README for the exact install and run commands. Their tests are skipped by the main test run unless the framework is installed.

| Example | What it shows | Used in |
| --- | --- | --- |
| [`11-langgraph`](../../examples/11-langgraph/README.md) | The weather agent as a state graph, tested with a fake chat model | [11.2](./11.2-langgraph.md) |
| [`11-crewai`](../../examples/11-crewai/README.md) | The weather agent as a one-agent crew, tested with a scripted `BaseLLM` | [11.3](./11.3-crewai.md) |
| [`11-agent-framework`](../../examples/11-agent-framework/README.md) | The weather agent in Microsoft Agent Framework, tested with a scripted chat client | [11.4](./11.4-microsoft-autogen-and-agent-framework.md) |
| [`11-autogen`](../../examples/11-autogen/README.md) | The same agent in archived AutoGen, for reading and migrating old code | [11.4](./11.4-microsoft-autogen-and-agent-framework.md) |
| [`11-openai-agents-sdk`](../../examples/11-openai-agents-sdk/README.md) | `Agent` + `Runner`, a handoff, tested with the SDK's `ScriptedModel` | [11.5](./11.5-openai-agents-sdk.md) |
| [`11-claude-agent-sdk`](../../examples/11-claude-agent-sdk/README.md) | The Claude Code harness with in-process MCP tools; live run needs an API key | [11.6](./11.6-claude-agent-sdk.md) |
| [`11-llamaindex`](../../examples/11-llamaindex/README.md) | A `FunctionAgent` with plain-function tools, tested with `MockFunctionCallingLLM` | [11.7](./11.7-llamaindex-agents.md) |
| [`11-pydantic-ai`](../../examples/11-pydantic-ai/README.md) | Typed tools and validation retries, tested with `FunctionModel` and `TestModel` | [11.8](./11.8-pydantic-ai.md) |
| [`01-anatomy-of-an-agent`](../../examples/01-anatomy-of-an-agent/README.md) | The no-framework baseline: the same agent over the shared LLM wrapper | [11.9](./11.9-the-no-framework-approach.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [10 · Multi-Agent Systems](../10-multi-agent-systems/README.md) ·
▶️ **Start reading:** [11.1 Framework landscape](./11.1-framework-landscape.md) ·
➡️ **Next chapter:** [12 · Evaluation](../12-evaluation/README.md)
