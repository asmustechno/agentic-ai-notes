# Agentic AI Notes

[![Content: CC BY 4.0](https://img.shields.io/badge/content-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE-CODE)
[![GitHub stars](https://img.shields.io/github/stars/asmustechno/agentic-ai-notes?style=social)](https://github.com/asmustechno/agentic-ai-notes/stargazers)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> **Zero se production tak: Agentic AI ki ek visual, example se bhari guide.**

Yeh AI agents banane par free, open study notes hain. Shuru karo bina agents ki kisi knowledge ke. Khatam karo aise ki tum production ke liye agent design, build, evaluate aur deploy kar sako.

Har idea ek hi tarike se samjhaya gaya hai: **pehle simple words, phir diagram, phir asli example, phir code.** Koi bhi term define kiye bina use nahi hota.

**Andar kya hai:** 19 chapters · 107 pages · har page par code snippets · 5 guided projects · 160+ terms ki [glossary](GLOSSARY.md) · ek page ki [cheatsheet](CHEATSHEET.md).

## 📑 Is page par

- [Yeh notes kiske liye hain](#-yeh-notes-kiske-liye-hain)
- [Inhe kaise padhein](#-inhe-kaise-padhein)
- [Table of contents](#-table-of-contents)
- [Licenses](#-licenses)
- [Contribute karo](#-contribute-karo)
- [Star history](#-star-history)

## 👋 Yeh notes kiske liye hain

- **Tumhe basic Python aati hai** aur tumne ChatGPT ya Claude use kiya hai.
- **Tumne kabhi agent nahi banaya**, ya tutorial copy karke banaya hai aur ab use achhe se samajhna chahte ho.
- **Tum experienced engineer ho** aur evaluation, safety, observability aur production design par ek clear reference chahte ho. 🔴 Advanced pages tumhare liye hain.

## 🧭 Inhe kaise padhein

Ek path chuno. Har path chapters ki ek list hai, order mein. Poora version [ROADMAP.md](ROADMAP.md) mein dekho.

| Path | Kiske liye | Chapters |
| --- | --- | --- |
| 🟢 **Beginner** | Samjho ki agents kya hain aur pehla agent banao | [00](docs/00-start-here/README.md) → [01](docs/01-foundations/README.md) → [02](docs/02-the-agent-loop/README.md) → [03](docs/03-tools-and-function-calling/README.md) → [Project 1](docs/18-projects/18.1-project-1-weather-and-calculator-agent.md) |
| 🟡 **Builder** | Memory, retrieval aur patterns ke saath kaam ke agents banao | Beginner path, phir [04](docs/04-model-context-protocol/README.md)–[11](docs/11-frameworks/README.md) → Projects 2–4 |
| 🔴 **Production** | Aise agents ship karo jo safe, measured aur affordable hon | Builder path, phir [12](docs/12-evaluation/README.md)–[17](docs/17-case-studies/README.md) → Project 5 |

Har page ki shape same hai, isliye tumhe hamesha pata rehta hai ki tum kahan ho:

```mermaid
flowchart LR
    A["🤔 Yeh kyun zaroori hai?"] --> B[🧠 Simple words mein] --> C[👀 Diagram] --> D[🔍 Step by step]
    D --> E[💡 Example se samjho] --> F[💻 Code] --> G[🚨 Aam galtiyan] --> H[🧪 Khud try karo]
```

*Har page "mujhe kyun parwaah karni chahiye?" se "ab khud try karo" tak jaata hai. Pehli baar padhte waqt chaho to code sections skip kar do; ideas apne aap mein poore hain.*

Jaise exam ki taiyari mein har chapter ka same pattern ho (theory, diagram, solved example, practice), waise hi yahan har page ek hi dhaanche mein hai.

Difficulty badges: 🟢 Beginner · 🟡 Intermediate · 🔴 Advanced. Koi word samajh nahi aaya? [Glossary](GLOSSARY.md) dekho.

## 📚 Table of contents

<!-- TOC:START -->
### [00 · Start Here](docs/00-start-here/README.md)

Yeh notes kaise kaam karte hain, kaunsa path follow karna hai, aur snippets chalane ke liye Python kaise set up karna hai. *(~20 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [0.1 In notes ko kaise use karein](docs/00-start-here/00.1-how-to-use-these-notes.md) | Notes kaise organise kiye gaye hain, har page mein kya hota hai, aur unhe kaise padhna hai. | 🟢 |
| [0.2 Learning paths](docs/00-start-here/00.2-learning-paths.md) | Material mein se teen raaste: Beginner, Builder aur Production. | 🟢 |
| [0.3 Setup](docs/00-start-here/00.3-setup.md) | Python aur model SDKs install karo, API key jodo, aur apna pehla snippet chalao. | 🟢 |

### [01 · Foundations](docs/01-foundations/README.md)

Agent kya hai, chatbot se kaise alag hai, aur woh parts jo har agent mein hote hain. *(~52 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [1.1 AI agent kya hai?](docs/01-foundations/01.1-what-is-an-ai-agent.md) | AI agent ki ek precise, simple-language definition. | 🟢 |
| [1.2 Chatbot, workflow aur agent mein farak](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md) | LLM systems ke teen type, aur unhe alag kaise pehchanein. | 🟢 |
| [1.3 Autonomy ka spectrum](docs/01-foundations/01.3-the-autonomy-spectrum.md) | Single prompt se le kar fully autonomous agent tak, ek-ek step kar ke. | 🟢 |
| [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md) | Tokens, context windows, temperature aur system prompts. | 🟢 |
| [1.5 Agent ke andar kya-kya hota hai](docs/01-foundations/01.5-anatomy-of-an-agent.md) | Model, instructions, tools, memory aur loop: har agent ke paanch parts. | 🟢 |
| [1.6 Agent kab use NAHI karna chahiye](docs/01-foundations/01.6-when-not-to-use-an-agent.md) | Woh signs jo batate hain ki simple solution tumhare liye behtar rahega. | 🟢 |

### [02 · The Agent Loop](docs/02-the-agent-loop/README.md)

Observe–think–act cycle jo har agent ke dil mein hai, bilkul zero se banaya hua. *(~51 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [2.1 Observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md) | Woh core cycle jo har agent chalata hai, step by step. | 🟢 |
| [2.2 ReAct ko samjho](docs/02-the-agent-loop/02.2-react-explained.md) | ReAct pattern, ek poore Thought → Action → Observation trace ke saath. | 🟢 |
| [2.3 50 lines mein agent, bilkul zero se](docs/02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md) | Bina framework ke, Python ki lagbhag 50 lines mein ek chalta hua agent likho. | 🟡 |
| [2.4 Agent kab ruke: stopping conditions](docs/02-the-agent-loop/02.4-stopping-conditions.md) | Max steps, timeouts, aur agent ko kaise pata chalta hai ki kaam ho gaya. | 🟡 |
| [2.5 Loop mein errors kaise sambhalein](docs/02-the-agent-loop/02.5-handling-errors-in-the-loop.md) | Tool failures, model ka galat output aur retries, bina run crash kiye. | 🟡 |

### [03 · Tools & Function Calling](docs/03-tools-and-function-calling/README.md)

Agents duniya mein kaam kaise karte hain, aur aise tools kaise design karein jinhe models achhe se use karein. *(~68 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [3.1 Tool kya hota hai?](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md) | Ek function jise chalane ko model tumse keh sakta hai, aur isse sab kuch kyun badal jaata hai. | 🟢 |
| [3.2 Tool definitions ke liye JSON Schema](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md) | Tool ke inputs aise describe karo ki model use sahi call kare. | 🟢 |
| [3.3 Function calling kaise kaam karta hai](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md) | Request → tool call → tool result round trip, do providers ke liye. | 🟢 |
| [3.4 Achhe tools kaise design karein](docs/03-tools-and-function-calling/03.4-designing-good-tools.md) | Aise names, descriptions, inputs aur error messages jo models samjhein. | 🟡 |
| [3.5 Parallel tool calls](docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md) | Ek turn mein kai tool calls, aur unke results kaise lautayein. | 🟡 |
| [3.6 Code execution ek tool ki tarah](docs/03-tools-and-function-calling/03.6-code-execution-as-a-tool.md) | Model ko code likhne aur chalane do, safely. | 🟡 |
| [3.7 Computer use aur browser agents](docs/03-tools-and-function-calling/03.7-computer-use-and-browser-agents.md) | Screens dekhne aur buttons click karne wale agents ka overview. | 🔴 |

### [04 · Model Context Protocol (MCP)](docs/04-model-context-protocol/README.md)

Agents ko tools aur data se jodne ka open standard. *(~64 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [4.1 MCP kyun bana?](docs/04-model-context-protocol/04.1-why-mcp-exists.md) | Woh integration problem jo MCP solve karta hai. | 🟢 |
| [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md) | MCP ke teen roles aur woh aapas mein kaise baat karte hain. | 🟢 |
| [4.3 Tools, resources aur prompts](docs/04-model-context-protocol/04.3-tools-resources-and-prompts.md) | Teen cheezein jo ek MCP server offer kar sakta hai. | 🟡 |
| [4.4 Ek simple MCP server banao](docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md) | Python mein apna pehla MCP server likho aur test karo. | 🟡 |
| [4.5 MCP ko agent se jodo](docs/04-model-context-protocol/04.5-connect-mcp-to-an-agent.md) | Apne agent loop se ek MCP server ke tools use karo. | 🟡 |
| [4.6 MCP servers ki security](docs/04-model-context-protocol/04.6-mcp-security.md) | Trust, permissions aur third-party servers ke risks. | 🔴 |

### [05 · Memory](docs/05-memory/README.md)

Agents ek task ke andar aur alag-alag tasks ke paar cheezein kaise yaad rakhte hain. *(~48 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [5.1 Short-term vs long-term memory](docs/05-memory/05.1-short-term-vs-long-term-memory.md) | Context window versus woh memory jo conversation ke baad bhi bachi rehti hai. | 🟢 |
| [5.2 Summarisation aur context compaction](docs/05-memory/05.2-summarisation-and-context-compaction.md) | Lambe runs ko context window ke andar rakho. | 🟡 |
| [5.3 Vector memory](docs/05-memory/05.3-vector-memory.md) | Memories ko keywords se nahi, matlab se store aur recall karo. | 🟡 |
| [5.4 Episodic, semantic aur procedural memory](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md) | Long-term memory ki teen kinds, aur har ek kis kaam ki hai. | 🟡 |
| [5.5 Memory design ke trade-offs](docs/05-memory/05.5-memory-design-trade-offs.md) | Kya store karna hai, kab recall karna hai, aur iska cost kya hai. | 🔴 |

### [06 · RAG for Agents](docs/06-rag-for-agents/README.md)

Retrieval-augmented generation, aur agents ise kaise smart banate hain. *(~49 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [6.1 RAG, 5 minute mein](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md) | Pehle retrieve, phir generate: poora idea paanch minute mein. | 🟢 |
| [6.2 Embeddings aur vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md) | Text kaise aise numbers banta hai jinhe search kar sako. | 🟢 |
| [6.3 Chunking ke tarike](docs/06-rag-for-agents/06.3-chunking-strategies.md) | Documents ko kaise todein taaki retrieval sahi tukda dhoondhe. | 🟡 |
| [6.4 Agentic RAG](docs/06-rag-for-agents/06.4-agentic-rag.md) | Agent khud decide karta hai ki kab, kya aur kaise retrieve karna hai. | 🟡 |
| [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md) | Jo retrieve karte ho, uski quality behtar karo aur measure karo. | 🔴 |

### [07 · Planning & Reasoning](docs/07-planning-and-reasoning/README.md)

Agents kaam karne se pehle kaise sochte hain, aur plan fail hone pe kaise sambhalte hain. *(~46 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [7.1 Chain-of-thought aur extended thinking](docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md) | Step-by-step reasoning, prompting tricks se le kar model ki built-in thinking tak. | 🟢 |
| [7.2 Plan-and-execute](docs/07-planning-and-reasoning/07.2-plan-and-execute.md) | Pehle plan banao, phir usko step by step poora karo. | 🟡 |
| [7.3 Task decomposition](docs/07-planning-and-reasoning/07.3-task-decomposition.md) | Bade goal ko chhote, check karne layak tasks mein todo. | 🟡 |
| [7.4 Tree-of-thoughts (ek overview)](docs/07-planning-and-reasoning/07.4-tree-of-thoughts.md) | Reasoning ki kai lines explore karo aur best wali rakho. | 🔴 |
| [7.5 Jab kuch fail ho, tab re-planning](docs/07-planning-and-reasoning/07.5-re-planning-when-things-fail.md) | Toota hua plan pehchano aur raasta badlo. | 🔴 |

### [08 · Reflection & Self-Correction](docs/08-reflection-and-self-correction/README.md)

Aise agents jo apna kaam khud check karke better banate hain, aur yeh kahan toot jaata hai. *(~36 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [8.1 Reflection pattern](docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md) | Draft, critique, revise. | 🟡 |
| [8.2 Evaluator–optimizer loop](docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md) | Ek model generate karta hai, doosra grade karta hai, aur loop chalta rehta hai. | 🟡 |
| [8.3 Tests ke saath self-critique](docs/08-reflection-and-self-correction/08.3-self-critique-with-tests.md) | Raay ki jagah test results jaise real signals use karo. | 🟡 |
| [8.4 Self-correction ki limits](docs/08-reflection-and-self-correction/08.4-limits-of-self-correction.md) | Jab agent apni galtiyan khud theek nahi kar sakta. | 🔴 |

### [09 · Agent Design Patterns](docs/09-agent-design-patterns/README.md)

Reusable building blocks, simple chains se lekar autonomous agents tak. *(~54 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [9.1 Prompt chaining](docs/09-agent-design-patterns/09.1-prompt-chaining.md) | Task ko fixed steps mein todo, har step ek LLM call. | 🟢 |
| [9.2 Routing](docs/09-agent-design-patterns/09.2-routing.md) | Input classify karo, phir use sahi handler ke paas bhejo. | 🟢 |
| [9.3 Parallelisation (sectioning aur voting)](docs/09-agent-design-patterns/09.3-parallelisation.md) | LLM calls ek saath chalao aur results combine karo. | 🟡 |
| [9.4 Orchestrator–workers](docs/09-agent-design-patterns/09.4-orchestrator-workers.md) | Ek lead model kaam baant ke workers ko deta hai. | 🟡 |
| [9.5 Evaluator–optimizer](docs/09-agent-design-patterns/09.5-evaluator-optimizer.md) | Generate-and-grade pattern ek reusable building block ki tarah. | 🟡 |
| [9.6 Human-in-the-loop](docs/09-agent-design-patterns/09.6-human-in-the-loop.md) | Ruko, taaki koi insaan approve, correct ya decide kar sake. | 🟡 |
| [9.7 Sahi pattern kaise chuno](docs/09-agent-design-patterns/09.7-choosing-a-pattern.md) | Sabse simple kaam karne wala pattern chunne ke liye ek decision flowchart. | 🟡 |

### [10 · Multi-Agent Systems](docs/10-multi-agent-systems/README.md)

Agents ki teams, woh aapas mein kaise coordinate karti hain, aur kab ek hi agent better hota hai. *(~54 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [10.1 Multiple agents kyun?](docs/10-multi-agent-systems/10.1-why-multiple-agents.md) | Kaam ko agents mein baantne se tumhe kya milta hai. | 🟡 |
| [10.2 Supervisor aur hierarchical](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md) | Ek manager agent specialist agents ko direct karta hai. | 🟡 |
| [10.3 Peer-to-peer aur handoffs](docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md) | Agents seedha ek dusre ko control pass karte hain. | 🟡 |
| [10.4 Shared state aur communication](docs/10-multi-agent-systems/10.4-shared-state-and-communication.md) | Agents ek dusre ke kaam par pair rakhe bina apni jaankari kaise share karte hain. | 🔴 |
| [10.5 Agent-to-agent protocols](docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md) | A2A jaise open protocols ka overview. | 🔴 |
| [10.6 Jab multi-agent cheezein aur bigaad deta hai](docs/10-multi-agent-systems/10.6-when-multi-agent-makes-things-worse.md) | Cost, latency aur coordination failures jin par nazar rakhni hai. | 🔴 |

### [11 · Frameworks](docs/11-frameworks/README.md)

Bade agent frameworks, jinme har ek same example agent ko dobara banata hai. *(~113 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [11.1 Frameworks ka poora naksha](docs/11-frameworks/11.1-framework-landscape.md) | Main agent frameworks ki ek comparison table. | 🟢 |
| [11.2 LangGraph](docs/11-frameworks/11.2-langgraph.md) | Agents ko nodes aur edges ke graph ki tarah banao, explicit state ke saath. | 🟡 |
| [11.3 CrewAI](docs/11-frameworks/11.3-crewai.md) | Role ke hisaab se bani agents ki crews jo tasks par kaam karti hain. | 🟡 |
| [11.4 Microsoft AutoGen aur Agent Framework](docs/11-frameworks/11.4-microsoft-autogen-and-agent-framework.md) | Microsoft ke multi-agent frameworks. | 🟡 |
| [11.5 OpenAI Agents SDK](docs/11-frameworks/11.5-openai-agents-sdk.md) | OpenAI ki taraf se agents, handoffs aur guardrails. | 🟡 |
| [11.6 Claude Agent SDK](docs/11-frameworks/11.6-claude-agent-sdk.md) | Claude Code ka agent harness, ek library ke roop mein. | 🟡 |
| [11.7 LlamaIndex agents](docs/11-frameworks/11.7-llamaindex-agents.md) | Data aur retrieval ke around bane agents. | 🟡 |
| [11.8 Pydantic AI](docs/11-frameworks/11.8-pydantic-ai.md) | Type-safe agents jinke inputs aur outputs validate hote hain. | 🟡 |
| [11.9 Bina framework wala tarika](docs/11-frameworks/11.9-the-no-framework-approach.md) | Kab provider SDK ke upar ek plain loop hi sabse sahi choice hai. | 🟡 |
| [11.10 Framework kaise choose karo](docs/11-frameworks/11.10-how-to-choose.md) | Aise sawal jo tumhe sahi tool tak le jaate hain. | 🟢 |

### [12 · Evaluation](docs/12-evaluation/README.md)

Kaise measure karein ki agent kaam karta hai, aur use kaam karta hua kaise rakhein. *(~58 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [12.1 Agents ke evals mushkil kyun hain?](docs/12-evaluation/12.1-why-agent-evals-are-hard.md) | Bahut saare steps, kai sahi raaste, aur har run par alag output. | 🟡 |
| [12.2 Task, trajectory aur tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) | Result, raasta aur tool calls, teeno ko measure karo. | 🟡 |
| [12.3 LLM-as-judge: model se grading karwao](docs/12-evaluation/12.3-llm-as-judge.md) | Outputs grade karne ke liye model use karo, aur grader ko bhi check karo. | 🟡 |
| [12.4 Eval dataset kaise banayein](docs/12-evaluation/12.4-building-an-eval-dataset.md) | Test cases collect, label aur maintain karo. | 🟡 |
| [12.5 CI mein agents ki regression testing](docs/12-evaluation/12.5-regression-testing-in-ci.md) | Har pull request par regressions pakdo. | 🔴 |
| [12.6 Public benchmarks (ek overview)](docs/12-evaluation/12.6-public-benchmarks.md) | Jaane-maane agent benchmarks aur unhe kaise padhein. | 🟡 |

### [13 · Safety & Guardrails](docs/13-safety-and-guardrails/README.md)

Woh threats jo sirf agents ke saath hote hain, aur unke khilaaf layered defences. *(~65 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [13.1 Agents ke liye threat model](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md) | Jab model actions le sakta hai, toh kya-kya galat ho sakta hai. | 🟡 |
| [13.2 Prompt injection aur uske defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md) | Direct aur indirect injection, aur nuksaan ko limit kaise karo. | 🔴 |
| [13.3 Least-privilege tools aur sandboxing](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md) | Agents ko sirf utna access do jitna zaroori hai. | 🔴 |
| [13.4 Input aur output guardrails](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md) | Jo andar jaata hai aur jo bahar aata hai, dono check karo. | 🟡 |
| [13.5 Risky actions ke liye human approval](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md) | Irreversible steps se pehle kisi insaan ka approval lo. | 🟡 |
| [13.6 Secrets aur PII handling](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md) | Keys aur personal data ko prompts, logs aur outputs se bahar rakho. | 🔴 |

### [14 · Observability & Debugging](docs/14-observability-and-debugging/README.md)

Dekho ki tumhare agent ne kya kiya, aur kyun, taaki tum use fix kar sako. *(~51 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [14.1 Agent runs ko trace karna](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md) | Run ke har step ko ek trace ki tarah record karo. | 🟡 |
| [14.2 Tool calls ko log karna](docs/14-observability-and-debugging/14.2-logging-tool-calls.md) | Har tool call ke liye kya log karna hai, aur kya kabhi nahi. | 🟢 |
| [14.3 LLM apps ke liye OpenTelemetry](docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md) | Agent systems ke liye standard traces aur spans. | 🔴 |
| [14.4 Tracing ke liye tools](docs/14-observability-and-debugging/14.4-tracing-tools.md) | LangSmith, Langfuse aur Arize Phoenix ka overview. | 🟡 |
| [14.5 Bigde hue agent ko debug karna](docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md) | Kya galat hua, yeh dhoondhne ka step-by-step tarika. | 🟡 |

### [15 · Production & Deployment](docs/15-production-and-deployment/README.md)

Ek chalte hue prototype ko reliable service mein badlo. *(~69 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [15.1 Production agent ka architecture](docs/15-production-and-deployment/15.1-production-architecture.md) | Loop ke around woh components jo use reliable banate hain. | 🔴 |
| [15.2 Sync vs async aur background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md) | Request-response agents vs lambe chalne wale jobs. | 🔴 |
| [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md) | Safely retry karo, bina koi kaam do baar kiye. | 🔴 |
| [15.4 State persistence aur resumability](docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md) | Progress save karo taaki crash ke baad run resume ho sake. | 🔴 |
| [15.5 Rate limits aur fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md) | Provider slow, busy ya down ho, tab bhi chalte raho. | 🔴 |
| [15.6 FastAPI aur Docker se deploy karna](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md) | Agent ko containerised web service ke roop mein ship karo. | 🔴 |

### [16 · Cost & Performance](docs/16-cost-and-performance/README.md)

Agents ko kharab kiye bina unhe sasta aur fast banao. *(~46 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [16.1 Token cost ka hisaab](docs/16-cost-and-performance/16.1-token-cost-maths.md) | Ek run ka cost kitna hai, worked examples ke saath nikaalo. | 🟢 |
| [16.2 Prompt caching](docs/16-cost-and-performance/16.2-prompt-caching.md) | Repeat hone wala context reuse karke cost aur latency kam karo. | 🟡 |
| [16.3 Model routing](docs/16-cost-and-performance/16.3-model-routing.md) | Aasaan kaam chhote models ko aur mushkil kaam bade models ko bhejo. | 🟡 |
| [16.4 Latency kam karna](docs/16-cost-and-performance/16.4-latency-optimisation.md) | Agent run mein time kahan jaata hai, aur use wapas kaise jeetein. | 🔴 |
| [16.5 Har run ki budget limits](docs/16-cost-and-performance/16.5-budget-limits-per-run.md) | Har run ke tokens, steps aur dollars cap karo. | 🟡 |

### [17 · Case Studies](docs/17-case-studies/README.md)

Paanch real-world agents, requirements se lekar failure modes tak. *(~63 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [17.1 Coding agent](docs/17-case-studies/17.1-coding-agent.md) | Ek agent jo code padhta, edit karta aur test karta hai. | 🔴 |
| [17.2 Customer support agent](docs/17-case-studies/17.2-customer-support-agent.md) | Sawalon ke jawab do, orders dekho, aur jaano kab human ko handoff karna hai. | 🟡 |
| [17.3 Research agent](docs/17-case-studies/17.3-research-agent.md) | Search karo, padho, aur ek cited report likho. | 🟡 |
| [17.4 Data analysis agent](docs/17-case-studies/17.4-data-analysis-agent.md) | Data se simple bhasha mein sawal poocho. | 🟡 |
| [17.5 Booking aur scheduling agent](docs/17-case-studies/17.5-booking-and-scheduling-agent.md) | Time dhoondho, book karo, aur confirm karo. | 🟡 |

### [18 · Projects](docs/18-projects/README.md)

Paanch guided, hands-on projects, har ek pichhle se thoda mushkil. *(~270 min)*

| Page | Kya seekhoge | Level |
| --- | --- | --- |
| [18.1 Project 1: Weather + calculator agent](docs/18-projects/18.1-project-1-weather-and-calculator-agent.md) | Tumhara pehla tool use karne wala agent. | 🟢 |
| [18.2 Project 2: Personal research assistant](docs/18-projects/18.2-project-2-research-assistant.md) | Web search aur sessions ke beech memory. | 🟡 |
| [18.3 Project 3: Tumhare PDFs par RAG agent](docs/18-projects/18.3-project-3-rag-over-your-pdfs.md) | Apne khud ke documents se sawal poocho. | 🟡 |
| [18.4 Project 4: Multi-agent content team](docs/18-projects/18.4-project-4-multi-agent-content-team.md) | Ek researcher, ek writer aur ek editor, saath mein kaam karte hue. | 🔴 |
| [18.5 Project 5: Production-ready support agent](docs/18-projects/18.5-project-5-production-support-agent.md) | Evals, guardrails aur tracing, shuru se end tak. | 🔴 |
<!-- TOC:END -->

Yeh [SUMMARY.md](SUMMARY.md) mein flat list ki tarah, [Glossary](GLOSSARY.md) ki tarah aur ek page ki [Cheatsheet](CHEATSHEET.md) ki tarah bhi available hai.

## 📜 Licenses

Is repository mein do licenses hain, ek words ke liye aur ek code ke liye:

| Kya | License | File | Short mein |
| --- | --- | --- | --- |
| Likha hua content (`docs/`, diagrams, baaki saara Markdown) | [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/) | [LICENSE](LICENSE) | Aazaadi se share aur adapt karo, commercially bhi, bas credit do aur wapas link karo. |
| Notes ke code snippets | [MIT](https://opensource.org/license/mit) | [LICENSE-CODE](LICENSE-CODE) | Code ko kisi bhi project mein use karo. Copyright notice rehne do. |

Do kyun? CC BY 4.0 prose aur images ke liye bana hai, lekin software ke liye recommended nahi hai. MIT code ke liye sabse simple permissive license hai. Dono milkar tumhe yahan ki har cheez bina jhanjhat ke reuse karne dete hain.

## 🤝 Contribute karo

Koi galti, toota link ya confusing explanation mila? [Issue kholo](.github/ISSUE_TEMPLATE/fix-content.md) ya pull request bhejo. Pehle [CONTRIBUTING.md](CONTRIBUTING.md) padho, aur hamara [Code of Conduct](CODE_OF_CONDUCT.md) follow karo.

**Contribute kaise karein, teen steps mein:**

1. Sudhaarne layak kuch dhoondho: confusing sentence, purani API, missing topic. Pehle [open issues](https://github.com/asmustechno/agentic-ai-notes/issues) check karo.
2. Repo fork karo, apna change karo, aur [CONTRIBUTING.md](CONTRIBUTING.md#-pull-request-kholne-se-pehle) ki checklist se guzro.
3. Pull request kholo. Template mein ek chhoti checklist hai.

Open source mein pehli baar contribute kar rahe ho? Typo ya toota link fix karna ekdum perfect shuruaat hai.

## ⭐ Star history

Agar in notes se tumhari madad hui, to ek star dusron ko inhe dhoondhne mein madad karta hai.

[![Star history chart](https://api.star-history.com/svg?repos=asmustechno/agentic-ai-notes&type=Date)](https://star-history.com/#asmustechno/agentic-ai-notes&Date)
