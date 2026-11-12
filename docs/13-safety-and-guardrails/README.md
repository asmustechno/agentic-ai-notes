🏠 [Home](../../README.md) › 13 · Safety & Guardrails

# 13 · Safety & Guardrails

> **Estimated reading time:** ~65 min · **Difficulty:** 🟡 Intermediate to 🔴 Advanced · **Prerequisites:** [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md), [12 · Evaluation](../12-evaluation/README.md) (helpful)

A chatbot that says something wrong is embarrassing. An agent that *does* something wrong can send your customer list to a stranger, delete a database or refund the wrong person. This chapter treats agent safety as a security problem: work out who could attack you and how, then stack several imperfect defences so that no single failure is a disaster. It is honest about the hard part: there is still no complete fix for prompt injection, so most of the work goes into limiting what a fooled agent *can* do.

## 🎯 What you'll learn

- How to threat-model an agent: assets, attackers, entry points, and the "lethal trifecta" of private data, untrusted content and external communication
- Direct and indirect prompt injection, and what each defence (marking, taint tracking, the dual-LLM pattern, CaMeL, human approval) does and does not stop
- Least privilege for tools: scoped credentials, read-only defaults, allowlists, network egress control and sandboxes
- How to build layered input and output guardrails that are easy to test
- How to put a human in front of irreversible actions without drowning them in approvals
- How to keep secrets and personal data out of prompts, logs and outputs

## 📋 Prerequisites

- [1.5 Anatomy of an agent](../01-foundations/01.5-anatomy-of-an-agent.md): the five parts you will be protecting
- [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md): the model *asks*, your code *runs*; that gap is where most defences live
- Basic Python, and the examples set up as in [0.3 Setup](../00-start-here/00.3-setup.md)

## 👀 Chapter overview

![Six defensive layers drawn as slices with holes: input guardrails, marking untrusted content, least-privilege tools, human approval, sandbox and egress control, and output guardrails with redaction. An attack arrow passes through holes in the first three layers and is stopped by human approval. Monitoring and an audit log run underneath every layer.](../../assets/diagrams/13-defence-in-depth.svg)

*No layer is perfect. The attack here slips past three of them and is caught by the fourth. Pages 13.2 to 13.6 each build one or two of these layers; 13.1 helps you decide which ones your agent needs.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 13.1 | [Threat model for agents](./13.1-threat-model-for-agents.md) — What can go wrong when a model can take actions. | 🟡 Intermediate | ~10 min |
| 13.2 | [Prompt injection & defences](./13.2-prompt-injection.md) — Direct and indirect injection, and how to limit the damage. | 🔴 Advanced | ~15 min |
| 13.3 | [Least-privilege tools & sandboxing](./13.3-least-privilege-and-sandboxing.md) — Give agents only the access they need. | 🔴 Advanced | ~12 min |
| 13.4 | [Input & output guardrails](./13.4-input-and-output-guardrails.md) — Check what goes in and what comes out. | 🟡 Intermediate | ~10 min |
| 13.5 | [Human approval for risky actions](./13.5-human-approval-for-risky-actions.md) — Require a person to approve irreversible steps. | 🟡 Intermediate | ~8 min |
| 13.6 | [Secrets & PII handling](./13.6-secrets-and-pii.md) — Keep keys and personal data out of prompts, logs and outputs. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

## 💻 Examples for this chapter

| Example | What it shows | Used in |
| --- | --- | --- |
| [`13-prompt-injection-demo`](../../examples/13-prompt-injection-demo/README.md) | A poisoned web page fools the agent; marking + taint tracking and the dual-LLM pattern stop the data leak anyway | [13.1](./13.1-threat-model-for-agents.md), [13.2](./13.2-prompt-injection.md), [13.3](./13.3-least-privilege-and-sandboxing.md) |
| [`13-guardrails`](../../examples/13-guardrails/README.md) | Layered input and output guards: length, deny list, injection flag, moderation hook, schema, refund limit, PII, link allowlist | [13.4](./13.4-input-and-output-guardrails.md) |
| [`13-approval-gate`](../../examples/13-approval-gate/README.md) | Risk tiers, dry-run previews, human approval and a JSONL audit log | [13.5](./13.5-human-approval-for-risky-actions.md) |
| [`13-pii-redaction`](../../examples/13-pii-redaction/README.md) | Reversible placeholders for emails, phones, cards and API keys, plus a redacting log filter | [13.6](./13.6-secrets-and-pii.md) |

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [12 · Evaluation](../12-evaluation/README.md) ·
▶️ **Start reading:** [13.1 Threat model for agents](./13.1-threat-model-for-agents.md) ·
➡️ **Next chapter:** [14 · Observability & Debugging](../14-observability-and-debugging/README.md)
