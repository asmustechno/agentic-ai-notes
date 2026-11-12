# 📖 Glossary

Every term used in these notes, A to Z. Each entry gives a short, plain definition and links to the page that explains it properly. Pages link here the first time they use a term.

> 🚧 This glossary grows as chapters are written. Missing a term? [Suggest it](.github/ISSUE_TEMPLATE/suggest-topic.md).

**Jump to:** [A](#a) · [C](#c) · [E](#e) · [F](#f) · [G](#g) · [L](#l) · [M](#m) · [P](#p) · [R](#r) · [S](#s) · [T](#t)

## A

### Agent

A system in which a [large language model](#large-language-model-llm) decides, step by step, which actions to take (usually by calling [tools](#tool)) to reach a goal, and keeps going until the goal is met or it stops. → [1.1 What is an AI agent?](docs/01-foundations/01.1-what-is-an-ai-agent.md)

### Agent loop

The repeating cycle at the heart of an agent: observe the current state, think about what to do, act (for example by calling a tool), then observe the result. → [2.1 The observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

## C

### Context window

The maximum amount of text, measured in [tokens](#token), that a model can read in one request. Everything the model "knows" about the current task must fit inside it. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## E

### Embedding

A list of numbers that represents the meaning of a piece of text. Texts with similar meanings have embeddings that are close together, which makes search by meaning possible. → [6.2 Embeddings & vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### Eval

Short for evaluation: a repeatable test that measures how well an LLM system performs on a set of example tasks. → [12.1 Why evals are hard for agents](docs/12-evaluation/12.1-why-agent-evals-are-hard.md)

## F

### Function calling

The model's ability to reply with a structured request to run one of the tools you described, instead of (or as well as) plain text. Your code runs the tool and sends the result back. Also called *tool calling* or *tool use*. → [3.3 How function calling works](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

## G

### Guardrail

A check that runs before or after a model call to block, fix or flag unsafe or invalid input and output. → [13.4 Input & output guardrails](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md)

## L

### Large language model (LLM)

A neural network trained on large amounts of text to predict the next [token](#token). Given a prompt, it generates text one token at a time. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## M

### MockLLM

A fake model used in these notes' examples. It returns pre-written responses, so every example and test can run offline, for free, and with the same result every time. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Model Context Protocol (MCP)

An open protocol that standardises how applications give models access to tools, data and prompts, so one integration works across many apps. → [4.1 Why MCP exists](docs/04-model-context-protocol/04.1-why-mcp-exists.md)

## P

### Prompt injection

An attack in which text the model reads, such as a user message, a web page or a tool result, contains instructions designed to override the developer's instructions. → [13.2 Prompt injection & defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## R

### ReAct

Short for "Reasoning and Acting": a pattern in which the model alternates between writing a reasoning step and taking an action, then reads the observation before continuing. Introduced by Yao et al. (2022). → [2.2 ReAct explained](docs/02-the-agent-loop/02.2-react-explained.md)

### Retrieval-augmented generation (RAG)

A technique that first retrieves relevant documents, then gives them to the model along with the question, so the answer is grounded in that information. → [6.1 RAG in 5 minutes](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md)

## S

### System prompt

Instructions given to the model separately from the user's messages, used to set its role, rules and behaviour for the whole conversation. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

## T

### Temperature

A sampling setting that controls how random a model's output is. Lower values make output more predictable; higher values make it more varied. Some newer models no longer accept it. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Token

The unit of text a model reads and writes: often a word, part of a word, or a punctuation mark. Context windows, limits and prices are all measured in tokens. → [1.4 How LLMs work](docs/01-foundations/01.4-how-llms-work.md)

### Tool

A function that your code exposes to the model, described by a name, a description and an input schema. The model can ask for it to be run; your code runs it and returns the result. → [3.1 What is a tool?](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md)
