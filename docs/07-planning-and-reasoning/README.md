🏠 [Home](../../README.md) › 07 · Planning & Reasoning

# 07 · Planning & Reasoning

> **Estimated reading time:** ~46 min · **Difficulty:** 🟢 Beginner to 🔴 Advanced · **Prerequisites:** [02 · The Agent Loop](../02-the-agent-loop/README.md)

A ReAct agent decides one step at a time. That is enough for short tasks, but longer ones need more: reasoning before acting, a plan that says what "done" means, and a way to recover when the plan meets reality. This chapter starts with how models reason (chain-of-thought prompting and built-in extended thinking), then builds plan-and-execute agents, shows how to decompose a goal into checkable sub-tasks, surveys tree-of-thoughts search, and ends with re-planning when a step fails.

## 🎯 What you'll learn

- Chain-of-thought prompting, built-in thinking on Claude and OpenAI models, and how to set reasoning effort
- When explicit "think step by step" prompting still helps, and when it doesn't
- The plan-and-execute pattern: a planner, an executor, and code that validates and schedules the plan
- How to decompose a goal into sub-tasks with done criteria and a dependency graph
- How tree of thoughts searches over partial solutions, and what that costs
- How to detect a failed step, re-plan the remaining work, and stop within limits

## 📋 Prerequisites

- [1.4 How LLMs work](../01-foundations/01.4-how-llms-work.md): tokens and output limits
- [2.2 ReAct explained](../02-the-agent-loop/02.2-react-explained.md) and [2.5 Handling errors in the loop](../02-the-agent-loop/02.5-handling-errors-in-the-loop.md)
- [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md)

## 👀 Chapter overview

![A goal goes to a planner model, which writes a plan of steps with dependencies and done-when criteria. An executor with tools runs one ready step at a time. A check sends the next step back to the executor, sends the user an answer when all steps are done, or, if a step failed, asks a re-planner for new steps for the remaining work.](../../assets/diagrams/07-plan-execute-replan.svg)

*The loop this chapter builds. The planner and re-planner think; the executor acts; your code checks each result and decides what happens next. Every model box can reason before it acts (7.1).*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 7.1 | [Chain-of-thought & extended thinking](./07.1-chain-of-thought-and-extended-thinking.md) — Step-by-step reasoning, from prompting tricks to built-in model thinking. | 🟢 Beginner | ~10 min |
| 7.2 | [Plan-and-execute](./07.2-plan-and-execute.md) — Make a plan first, then carry it out step by step. | 🟡 Intermediate | ~10 min |
| 7.3 | [Task decomposition](./07.3-task-decomposition.md) — Break a big goal into small, checkable tasks. | 🟡 Intermediate | ~8 min |
| 7.4 | [Tree-of-thoughts (overview)](./07.4-tree-of-thoughts.md) — Explore several lines of reasoning and keep the best. | 🔴 Advanced | ~8 min |
| 7.5 | [Re-planning when things fail](./07.5-re-planning-when-things-fail.md) — Notice a broken plan and change course. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

All examples run offline with `MockLLM` and fake-data tools, and also work with a real model (`LLM_PROVIDER=anthropic|openai`).

| Example | What it shows | Used in |
| --- | --- | --- |
| [`07-chain-of-thought`](../../examples/07-chain-of-thought/README.md) | Direct vs chain-of-thought prompts, extracting the answer from `<answer>` tags | [7.1](./07.1-chain-of-thought-and-extended-thinking.md) |
| [`07-plan-and-execute`](../../examples/07-plan-and-execute/README.md) | A JSON plan validated in code, run in dependency order by a tool-using executor | [7.2](./07.2-plan-and-execute.md), [7.3](./07.3-task-decomposition.md) |
| [`07-tree-of-thoughts`](../../examples/07-tree-of-thoughts/README.md) | Breadth-first tree of thoughts on the Game of 24, with the cost in model calls | [7.4](./07.4-tree-of-thoughts.md) |
| [`07-replanning`](../../examples/07-replanning/README.md) | A failed step triggers a re-plan of the remaining work, with limits and giving up | [7.5](./07.5-re-planning-when-things-fail.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [06 · RAG for Agents](../06-rag-for-agents/README.md) ·
▶️ **Start reading:** [7.1 Chain-of-thought & extended thinking](./07.1-chain-of-thought-and-extended-thinking.md) ·
➡️ **Next chapter:** [08 · Reflection & Self-Correction](../08-reflection-and-self-correction/README.md)
