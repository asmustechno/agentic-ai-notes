# Launch kit

Everything needed to publish the repository and announce it.

## Repository description

Use this in **Settings → General → Description** (GitHub allows up to 350 characters):

> From zero to production: a visual, example-driven guide to building AI agents. 19 chapters, 107 pages, Mermaid diagrams and Python code snippets on every page. Covers the agent loop, tools, MCP, memory, RAG, planning, multi-agent systems, frameworks, evals, safety, observability, deployment and cost.

## Topics

Add these 10 in **About → Topics**:

`agentic-ai` · `ai-agents` · `llm` · `mcp` · `rag` · `langgraph` · `multi-agent-systems` · `prompt-engineering` · `python` · `tutorial`

## Social preview

**Settings → General → Social preview**: upload a 1280×640 image. A simple option is a screenshot of `assets/diagrams/01-anatomy-of-an-agent.svg` on a white background with the title "Agentic AI Notes: from zero to production".

## Launch post (LinkedIn)

Copy and paste; LinkedIn keeps the line breaks.

```text
I've published Agentic AI Notes: a free, open guide to building AI agents, from zero to production. 🧠🔧

Most agent tutorials stop at "paste your API key and run this". I wanted something that explains why things work, and what breaks in production.

Every topic follows the same path: plain words → a diagram → a worked example → code.

What's inside:
🟢 Foundations: what an agent really is, the agent loop, tools and function calling
🟡 Building: MCP, memory, RAG, planning, reflection, design patterns, multi-agent systems, and 8 frameworks compared on the same task
🔴 Production: evals, prompt-injection defences, tracing with OpenTelemetry, deployment, and cost maths

Every page has short Python snippets for both Claude and OpenAI, and there are 5 guided projects to build along the way.

It's open source: content under CC BY 4.0, code under MIT. Corrections and PRs are very welcome.

👉 https://github.com/asmustechno/agentic-ai-notes

#AI #AIAgents #LLM #AgenticAI #OpenSource #Python
```

## Launch post (X / short form)

```text
I wrote a free, open guide to building AI agents, from zero to production.

Plain words → diagram → example → code, for every topic: agent loop, tools, MCP, memory, RAG, evals, safety, deployment, cost.

Code snippets on every page, plus 5 guided projects.

https://github.com/asmustechno/agentic-ai-notes
```

## Before you announce: checklist

- [ ] Replace `TODO-MAINTAINER-CONTACT` in `CODE_OF_CONDUCT.md` with a real contact
- [ ] Push to GitHub and click through a few pages to check that diagrams and links render
- [ ] Add the description, topics and social preview above
- [ ] Turn on **Issues** and **Discussions**, and pin a "Start here" discussion that links to the README
