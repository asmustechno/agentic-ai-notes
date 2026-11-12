# 📖 Glossary

Every term used in these notes, A to Z. Each entry gives a short, plain definition and links to the page that explains it properly. Pages link here the first time they use a term.

> 🚧 This glossary grows as chapters are written. Missing a term? [Suggest it](.github/ISSUE_TEMPLATE/suggest-topic.md).

**Jump to:** [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [L](#l) · [M](#m) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [V](#v) · [W](#w)

## A

### Agent

A system in which a [large language model](#large-language-model-llm) decides, step by step, which actions to take (usually by calling [tools](#tool)) to reach a goal, and keeps going until the goal is met or it stops. → [1.1 What is an AI agent?](docs/01-foundations/01.1-what-is-an-ai-agent.md)

### Agent loop

The repeating cycle at the heart of an agent: observe the current state, think about what to do, act (for example by calling a tool), then observe the result. → [2.1 The observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

### API key

A secret string that identifies you to a model provider and lets your code call its API. Keep it in a `.env` file, never in code. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Autonomy spectrum

A scale describing how much an LLM system's model decides, from a single prompt (code decides everything) to a fully autonomous agent (the model sets its own sub-goals). → [1.3 The autonomy spectrum](docs/01-foundations/01.3-the-autonomy-spectrum.md)

## B

### Benchmark

A public, standardised set of tasks with a fixed way of grading them, used to compare models or agent systems. A score describes the whole system tested (model plus scaffold), on that benchmark's tasks only. → [12.6 Public benchmarks (overview)](docs/12-evaluation/12.6-public-benchmarks.md)

## C

### Chatbot

A system that answers with a single model reply per message and takes no actions. It can only use what the model already knows or what is in the prompt. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

### Compounding errors

The way small per-step error rates add up over many steps: if each step is right with probability p, all n steps are right with probability pⁿ. A key reason long agent runs need ways to catch mistakes. → [1.6 When NOT to use an agent](docs/01-foundations/01.6-when-not-to-use-an-agent.md)

### Context window

The maximum amount of text, measured in [tokens](#token), that a model can read in one request. Everything the model "knows" about the current task must fit inside it. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## D

### Data contamination

When benchmark or test questions (or their answers) end up in a model's training data, so its score partly reflects memorisation and overstates how well it handles new problems. → [12.6 Public benchmarks (overview)](docs/12-evaluation/12.6-public-benchmarks.md)

## E

### Embedding

A list of numbers that represents the meaning of a piece of text. Texts with similar meanings have embeddings that are close together, which makes search by meaning possible. → [6.2 Embeddings & vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### Environment variable

A named setting passed to a program by its environment rather than written in its code, such as `LLM_PROVIDER=mock`. The examples read them from a `.env` file. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Eval

Short for evaluation: a repeatable test that measures how well an LLM system performs on a set of example tasks. → [12.1 Why evals are hard for agents](docs/12-evaluation/12.1-why-agent-evals-are-hard.md)

## F

### Function calling

The model's ability to reply with a structured request to run one of the tools you described, instead of (or as well as) plain text. Your code runs the tool and sends the result back. Also called *tool calling* or *tool use*. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

## G

### Guardrail

A check that runs before or after a model call to block, fix or flag unsafe or invalid input and output. → [13.4 Input & output guardrails](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md)

## H

### Hallucination

When a model states something false or invented as if it were true, such as a delivery date it had no data for. Giving the model real data through tools or retrieval reduces it. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

## I

### Instructions

The part of an agent that tells the model its role, goal, rules and how to use its tools, usually written as the system prompt. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## L

### Large language model (LLM)

A neural network trained on large amounts of text to predict the next [token](#token). Given a prompt, it generates text one token at a time. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### LLM-as-judge

Using a language model to grade another model's or agent's output against a rubric, returning a structured verdict. It needs checking against human labels before you trust it. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

### Long-term memory

Information an agent keeps between runs, such as user preferences, past results or documents. Code stores it and puts relevant parts back into the context when needed. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## M

### Max tokens

The limit you set on how many tokens the model may write in one reply. If it is reached, the reply is cut off and the stop reason says so. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### MockLLM

A fake model used in these notes' examples. It returns pre-written responses, so every example and test can run offline, for free, and with the same result every time. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Model Context Protocol (MCP)

An open protocol that standardises how applications give models access to tools, data and prompts, so one integration works across many apps. → [4.1 Why MCP exists](docs/04-model-context-protocol/04.1-why-mcp-exists.md)

## P

### pass@k (pass at k)

The chance that at least one of k independent attempts at a task succeeds. It rises towards 1 as k grows, and suits tasks where you can automatically pick the attempt that worked. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### pass^k (pass hat k)

The chance that all k independent attempts at a task succeed. It falls as k grows, and measures the consistency that customer-facing agents need. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Position bias

A judge model's tendency to prefer an answer because of where it appears (for example, first) rather than what it says. Countered by asking twice with the order swapped. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

### Prompt injection

An attack in which text the model reads, such as a user message, a web page or a tool result, contains instructions designed to override the developer's instructions. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## R

### ReAct

Short for "Reasoning and Acting": a pattern in which the model alternates between writing a reasoning step and taking an action, then reads the observation before continuing. Introduced by Yao et al. (2022). → [2.2 ReAct explained](docs/02-the-agent-loop/02.2-react-explained.md)

### Retrieval-augmented generation (RAG)

A technique that first retrieves relevant documents, then gives them to the model along with the question, so the answer is grounded in that information. → [6.1 RAG in 5 minutes](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md)

### Rubric

A written list of criteria, each with a clear pass/fail rule, that a human or model grader uses so that grading is consistent. → [12.3 LLM-as-judge](docs/12-evaluation/12.3-llm-as-judge.md)

## S

### Sampling

How a model picks each next token from its predicted probabilities, rather than always taking the most likely one. It is why the same prompt can give different replies. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Short-term memory

What an agent knows during the current run: the conversation so far, including every tool call and result. It lives in the context window. → [1.5 Anatomy of an agent](docs/01-foundations/01.5-anatomy-of-an-agent.md)

### Stateless

Describes an API that keeps no memory between calls. LLM APIs are stateless, so your code must resend the conversation every time. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Stop reason

The field in a model's reply that says why it stopped writing: it finished, it wants to call a tool, it hit the output limit, or it refused. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### System prompt

Instructions given to the model separately from the user's messages, used to set its role, rules and behaviour for the whole conversation. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## T

### Temperature

A sampling setting that controls how random a model's output is: lower is more predictable, higher is more varied. Several recent models no longer accept it, and even at 0 outputs can vary. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Token

The unit of text a model reads and writes: often a word, part of a word, or a punctuation mark. Context windows, limits and prices are all measured in tokens. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Tokenizer

The component that splits text into tokens before the model reads it. Each provider has its own, so the same text gives different token counts on different models. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Tool

A function that your code exposes to the model, described by a name, a description and an input schema. The model can ask for it to be run; your code runs it and returns the result. → [3.1 What is a tool?](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md)

### Trajectory

The ordered list of steps an agent took in one run, especially its tool calls and their arguments. Evals compare it with an expected trajectory to check the path, not just the result. → [12.2 Task, trajectory & tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Transformer

The neural network architecture behind modern LLMs, introduced in 2017. It lets each token take every earlier token into account when predicting the next one. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## V

### Virtual environment

A self-contained folder of Python packages for one project, so its dependencies do not clash with other projects. Created with `python -m venv .venv`. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

## W

### Workflow

An LLM system in which your code fixes the sequence of steps in advance and the model fills in parts, such as writing text or classifying input. Contrast with an agent, where the model chooses the steps. → [1.2 Chatbot vs workflow vs agent](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)
