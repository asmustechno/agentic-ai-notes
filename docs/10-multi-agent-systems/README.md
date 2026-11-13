🏠 [Home](../../README.md) › 10 · Multi-Agent Systems

# 10 · Multi-Agent Systems

> **Estimated reading time:** ~54 min · **Difficulty:** 🟡 Intermediate to 🔴 Advanced · **Prerequisites:** [02 · The Agent Loop](../02-the-agent-loop/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md), [09 · Agent Design Patterns](../09-agent-design-patterns/README.md)

Sometimes one agent isn't enough: the task is too broad for one context, or its parts are better done in parallel by specialists. This chapter shows how teams of agents are organised (supervisors, handoffs and shared state), how independent agents from different organisations talk through open protocols such as A2A, and, just as important, when a team of agents costs more and does worse than one good agent.

## 🎯 What you'll learn

- What splitting work across agents buys you: separation of concerns, parallel exploration, context isolation and specialised tools
- The supervisor pattern: a lead agent that delegates to specialist agents exposed as tools, and how to write a good brief
- Handoffs: passing control of a conversation from one agent to another, as in the OpenAI Agents SDK
- How agents share information through messages or a shared blackboard, and how to stop them overwriting each other
- The A2A protocol: Agent Cards, tasks, messages and artifacts, and how A2A relates to MCP
- The costs and failure modes of multi-agent systems, and a checklist for deciding when not to use them

## 📋 Prerequisites

- [1.5 Anatomy of an agent](../01-foundations/01.5-anatomy-of-an-agent.md): every agent in a team is an ordinary agent
- [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md): agents call each other through tools
- [9.4 Orchestrator-workers](../09-agent-design-patterns/09.4-orchestrator-workers.md): the workflow the supervisor pattern grows from
- Helpful for 10.5: [4.1 Why MCP exists](../04-model-context-protocol/04.1-why-mcp-exists.md)

## 👀 Chapter overview

![Four ways to arrange agents. One agent: an agent calls its tools. Supervisor: a supervisor sends briefs to two specialists and gets reports back. Handoffs: triage transfers control to billing or tech, which can transfer to each other. Shared state: two agents read and write a shared blackboard with versioned keys.](../../assets/diagrams/10-multi-agent-topologies.svg)

*Start on the left and move right only when you must. Pages 10.2, 10.3 and 10.4 cover panels ②, ③ and ④. Page 10.5 connects agents across organisations, and 10.6 explains why panel ① is often the right answer.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 10.1 | [Why multiple agents?](./10.1-why-multiple-agents.md) — What splitting work across agents buys you. | 🟡 Intermediate | ~8 min |
| 10.2 | [Supervisor & hierarchical](./10.2-supervisor-and-hierarchical.md) — A manager agent directs specialist agents. | 🟡 Intermediate | ~10 min |
| 10.3 | [Peer-to-peer & handoffs](./10.3-peer-to-peer-and-handoffs.md) — Agents pass control to each other directly. | 🟡 Intermediate | ~10 min |
| 10.4 | [Shared state & communication](./10.4-shared-state-and-communication.md) — How agents share what they know without stepping on each other. | 🔴 Advanced | ~10 min |
| 10.5 | [Agent-to-agent protocols](./10.5-agent-to-agent-protocols.md) — An overview of open protocols such as A2A. | 🔴 Advanced | ~8 min |
| 10.6 | [When multi-agent makes things worse](./10.6-when-multi-agent-makes-things-worse.md) — Cost, latency and coordination failures to watch for. | 🔴 Advanced | ~8 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [09 · Agent Design Patterns](../09-agent-design-patterns/README.md) ·
▶️ **Start reading:** [10.1 Why multiple agents?](./10.1-why-multiple-agents.md) ·
➡️ **Next chapter:** [11 · Frameworks](../11-frameworks/README.md)
