🏠 [Home](../../README.md) › 05 · Memory

# 05 · Memory

> **Estimated reading time:** ~48 min · **Difficulty:** 🟢 Beginner to 🔴 Advanced · **Prerequisites:** [01 · Foundations](../01-foundations/README.md), [02 · The Agent Loop](../02-the-agent-loop/README.md)

A model remembers nothing between calls. Everything an agent "knows" about the current task, and about the user from last week, has to be put back into the context by your code. This chapter is about doing that well. It separates short-term memory (the context window) from long-term memory (what you store outside the model), shows how to keep long runs inside their budget with trimming, summarisation and provider-side compaction, builds a vector memory that recalls by similarity, splits long-term memory into episodic, semantic and procedural kinds, and ends with the design decisions that make memory helpful rather than creepy: what to store, when to recall, staleness, privacy, cost and evaluation.

## 🎯 What you'll learn

- The difference between short-term memory (the context window) and long-term memory, and the write, store, recall, inject cycle
- Three ways to keep a long conversation within budget: trimming, rolling summaries and clearing old tool results
- How Anthropic's server-side compaction and context editing, and OpenAI's Responses API compaction, work
- How vector memory stores embeddings and recalls by cosine similarity, and why real systems need an embedding model
- Episodic, semantic and procedural memory (from the CoALA paper), and Anthropic's memory tool
- The trade-offs: what to store, when to write and recall, staleness, privacy and PII, cost and evaluation

## 📋 Prerequisites

- [1.4 How LLMs work](../01-foundations/01.4-how-llms-work.md): tokens, context windows and statelessness
- [1.5 Anatomy of an agent](../01-foundations/01.5-anatomy-of-an-agent.md): memory as one of the five parts
- [2.3 A 50-line agent from scratch](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md): the loop the examples build on
- [0.3 Setup](../00-start-here/00.3-setup.md), so you can run the examples

## 👀 Chapter overview

![The context window in the centre holds instructions, recalled memories, a summary of older turns and recent turns; the model reads all of it on every call. Older turns are summarised into it from the left. On the right, long-term memory holds semantic facts, episodic past runs, procedural rules and a vector index; memories are recalled into the context and written back out.](../../assets/diagrams/05-memory-map.svg)

*Page 5.1 explains the two halves of this picture. Page 5.2 is the "summarise" arrow on the left. Pages 5.3 and 5.4 are the long-term stores on the right, and 5.5 is about the "recall" and "write" arrows between them.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 5.1 | [Short-term vs long-term memory](./05.1-short-term-vs-long-term-memory.md) — The context window versus memory that outlives a conversation. | 🟢 Beginner | ~8 min |
| 5.2 | [Summarisation & context compaction](./05.2-summarisation-and-context-compaction.md) — Keep long runs inside the context window. | 🟡 Intermediate | ~10 min |
| 5.3 | [Vector memory](./05.3-vector-memory.md) — Store and recall memories by meaning, not keywords. | 🟡 Intermediate | ~10 min |
| 5.4 | [Episodic, semantic & procedural memory](./05.4-episodic-semantic-and-procedural-memory.md) — Three kinds of long-term memory and what each is for. | 🟡 Intermediate | ~10 min |
| 5.5 | [Memory design trade-offs](./05.5-memory-design-trade-offs.md) — What to store, when to recall, and what it costs. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

| Example | What it shows | Used in |
| --- | --- | --- |
| [`05-summarising-memory`](../../examples/05-summarising-memory/README.md) | Trimming versus a rolling summary on the same eight-turn chat, with a token budget | [5.2](./05.2-summarisation-and-context-compaction.md) |
| [`05-vector-memory`](../../examples/05-vector-memory/README.md) | `remember` and `recall` tools over a vector store that survives between sessions; a toy offline embedder and where it fails | [5.1](./05.1-short-term-vs-long-term-memory.md), [5.3](./05.3-vector-memory.md) |
| [`05-memory-types`](../../examples/05-memory-types/README.md) | Separate semantic, episodic and procedural stores filled by a reflection step, with PII redaction and updates | [5.4](./05.4-episodic-semantic-and-procedural-memory.md), [5.5](./05.5-memory-design-trade-offs.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [04 · Model Context Protocol (MCP)](../04-model-context-protocol/README.md) ·
▶️ **Start reading:** [5.1 Short-term vs long-term memory](./05.1-short-term-vs-long-term-memory.md) ·
➡️ **Next chapter:** [06 · RAG for Agents](../06-rag-for-agents/README.md)
