🏠 [Home](../../README.md) › 06 · RAG for Agents

# 06 · RAG for Agents

> **Estimated reading time:** ~49 min · **Difficulty:** 🟢 Beginner to 🔴 Advanced · **Prerequisites:** [01 · Foundations](../01-foundations/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md)

Models only know what they were trained on and what you put in the prompt. Retrieval-augmented generation (RAG) puts the right pieces of *your* documents in the prompt, so answers are grounded in your facts and can cite them. This chapter goes from the basic retrieve-then-generate idea, through embeddings, vector databases and chunking, to agentic RAG, where the agent decides when and what to search, and finishes with how to improve retrieval and measure it.

## 🎯 What you'll learn

- What RAG is, and why most RAG failures are really retrieval failures
- What embeddings are, how cosine similarity and ANN indexes work, and how to pick a vector store
- Five ways to chunk documents, and how a bad cut produces a confident wrong answer
- How to turn retrieval into a tool so an agent can rewrite queries, search more than once, and say "not found"
- Hybrid search (BM25 + vectors) with reciprocal rank fusion, and re-ranking with cross-encoders
- How to measure retrieval with recall@k, precision@k, MRR and nDCG on a labelled eval set

## 📋 Prerequisites

- [1.4 How LLMs work](../01-foundations/01.4-how-llms-work.md): tokens and context windows
- [1.5 Anatomy of an agent](../01-foundations/01.5-anatomy-of-an-agent.md): the model, tools, memory and loop
- [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md), for agentic RAG (6.4)
- Helpful but optional: [5.3 Vector memory](../05-memory/05.3-vector-memory.md)

## 👀 Chapter overview

![Two lanes. Ahead of time, documents are chunked, embedded and stored in a vector index plus a keyword index. At question time, the user's question goes to an agent, which calls a search_docs tool running hybrid search and re-ranking over the index, reads the results, may search again, and answers with citations or says "not found".](../../assets/diagrams/06-rag-pipeline.svg)

*Indexing (top) happens once per document; retrieval (bottom) happens per question. Each box is labelled with the page that covers it. In agentic RAG the agent sits between the user and the search tool, so it can search zero, one or several times.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 6.1 | [RAG in 5 minutes](./06.1-rag-in-5-minutes.md) — Retrieve, then generate: the whole idea in five minutes. | 🟢 Beginner | ~5 min |
| 6.2 | [Embeddings & vector databases](./06.2-embeddings-and-vector-databases.md) — How text becomes numbers you can search. | 🟢 Beginner | ~10 min |
| 6.3 | [Chunking strategies](./06.3-chunking-strategies.md) — How to split documents so retrieval finds the right piece. | 🟡 Intermediate | ~10 min |
| 6.4 | [Agentic RAG](./06.4-agentic-rag.md) — The agent decides when, what and how to retrieve. | 🟡 Intermediate | ~12 min |
| 6.5 | [Re-ranking & retrieval evaluation](./06.5-re-ranking-and-retrieval-evaluation.md) — Improve and measure the quality of what you retrieve. | 🔴 Advanced | ~12 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

Every example runs offline. The retrieval in them is a tiny pure-Python stand-in (hashed bag-of-words, character trigrams, BM25); real systems use an embedding model and a vector database, as explained in 6.2.

| Example | What it shows | Used in |
| --- | --- | --- |
| [`06-agentic-rag`](../../examples/06-agentic-rag/README.md) | Classic RAG vs an agent with a `search_docs` tool: multi-hop, query rewriting, "not found" | [6.1](./06.1-rag-in-5-minutes.md), [6.2](./06.2-embeddings-and-vector-databases.md), [6.4](./06.4-agentic-rag.md) |
| [`06-chunking`](../../examples/06-chunking/README.md) | Five chunking strategies compared on the same questions | [6.3](./06.3-chunking-strategies.md) |
| [`06-retrieval-eval`](../../examples/06-retrieval-eval/README.md) | BM25, vectors, RRF hybrid and re-ranking scored with recall@k, precision@k, MRR and nDCG | [6.5](./06.5-re-ranking-and-retrieval-evaluation.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [05 · Memory](../05-memory/README.md) ·
▶️ **Start reading:** [6.1 RAG in 5 minutes](./06.1-rag-in-5-minutes.md) ·
➡️ **Next chapter:** [07 · Planning & Reasoning](../07-planning-and-reasoning/README.md)
