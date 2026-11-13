🏠 [Home](../../README.md) › 11 · Frameworks

# 11 · Frameworks

> **Padhne ka time:** ~113 min · **Level:** 🟡 Intermediate · **Pehle padho:** [01 · Foundations](../01-foundations/README.md), [02 · The Agent Loop](../02-the-agent-loop/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md)

Aaj itne agent frameworks aa gaye hain ki koi sab try nahi kar sakta. Yeh chapter tumhe pehle ek map deta hai. Phir **ek hi agent** ko (Paris-vs-Rome weather agent, jo [1.5](../01-foundations/01.5-anatomy-of-an-agent.md) mein bana tha) har framework mein dobara banata hai: LangGraph, CrewAI, Microsoft Agent Framework (aur archived AutoGen), OpenAI Agents SDK, Claude Agent SDK, LlamaIndex aur Pydantic AI. Isse tum barabar ki cheezon ko barabar compare kar paoge.

Chapter ke end mein yeh bhi samjhaya hai ki kab koi framework use hi mat karo. Aur framework choose karne ka ek chhota process bhi hai. Har page dikhata hai ki us framework ke apne fake model se agent ko offline kaise test karo. Har page yeh bhi batata hai ki kaunse exact package version par check kiya gaya.

## 🎯 Is chapter mein kya seekhoge

- Har framework agent ke paanch parts (model, instructions, tools, memory aur loop) ko kis naam se aur kaise package karta hai
- Har framework ka core abstraction: state graphs, crews, agents aur workflows, runners aur handoffs, ek harness, query-engine tools, typed outputs
- Microsoft AutoGen (archived) ka abhi kya status hai, aur uska successor Microsoft Agent Framework
- Claude Agent SDK (ek poora agent harness) Anthropic SDK ke tool runner se kaise alag hai
- Har framework mein uske fake ya scripted model se agents ko offline kaise test karo
- Kab provider SDK ke upar ek plain loop kisi bhi framework se better hota hai
- Sawalon ke through framework choose karne ka tarika, aur apne options khule kaise rakho

## 📋 Pehle se kya aana chahiye

- [1.5 Agent ke andar kya-kya hota hai](../01-foundations/01.5-anatomy-of-an-agent.md): woh paanch parts jo har framework package karta hai
- [2.3 50 lines mein agent, bilkul zero se](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md): woh loop jo frameworks chhupa dete hain
- [3.3 Function calling kaise kaam karta hai](../03-tools-and-function-calling/03.3-how-function-calling-works.md): jab model koi tool call karta hai tab kya hota hai
- Kuch pages ke liye kaam ka: [4.1 MCP kyun bana?](../04-model-context-protocol/04.1-why-mcp-exists.md) (Claude Agent SDK), [6.1 RAG, 5 minute mein](../06-rag-for-agents/06.1-rag-in-5-minutes.md) (LlamaIndex), [10.1 Multiple agents kyun?](../10-multi-agent-systems/10.1-why-multiple-agents.md) (CrewAI, handoffs, workflows)
- Python 3.11, aur har example ke liye alag [virtual environment](../../GLOSSARY.md#virtual-environment) banana aana chahiye

## 👀 Chapter ek nazar mein

![Agent tooling ki chaar layers, neeche se upar. Sabse neeche tumhara apna loop provider SDK ke upar, ya Anthropic SDK ka tool runner. Uske upar agent SDKs jo tumhare liye loop chalate hain: OpenAI Agents SDK, Pydantic AI, LlamaIndex agents, Microsoft Agent Framework. Uske upar orchestration frameworks jahan control flow tum design karte ho: LangGraph, CrewAI, Agent Framework workflows, LlamaIndex workflows. Sabse upar harnesses jinme built-in tools aur permissions hote hain: Claude Agent SDK, LangChain Deep Agents, Agent Framework ka harness agent.](../../assets/diagrams/11-framework-layers.svg)

*Yeh chapter isi picture par chalta hai. 11.1 iska map deta hai, 11.2–11.8 har framework ko same example ke saath dekhte hain, 11.9 sabse neeche wali layer cover karta hai, aur 11.10 decide karne mein help karta hai ki tumhe kitna upar jaana hai.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 11.1 | [Frameworks ka poora naksha](./11.1-framework-landscape.md) — Main agent frameworks ki ek comparison table. | 🟢 Beginner | ~8 min |
| 11.2 | [LangGraph](./11.2-langgraph.md) — Agents ko nodes aur edges ke graph ki tarah banao, explicit state ke saath. | 🟡 Intermediate | ~15 min |
| 11.3 | [CrewAI](./11.3-crewai.md) — Role ke hisaab se bani agents ki crews jo tasks par kaam karti hain. | 🟡 Intermediate | ~12 min |
| 11.4 | [Microsoft AutoGen aur Agent Framework](./11.4-microsoft-autogen-and-agent-framework.md) — Microsoft ke multi-agent frameworks. | 🟡 Intermediate | ~12 min |
| 11.5 | [OpenAI Agents SDK](./11.5-openai-agents-sdk.md) — OpenAI ki taraf se agents, handoffs aur guardrails. | 🟡 Intermediate | ~12 min |
| 11.6 | [Claude Agent SDK](./11.6-claude-agent-sdk.md) — Claude Code ka agent harness, ek library ke roop mein. | 🟡 Intermediate | ~12 min |
| 11.7 | [LlamaIndex agents](./11.7-llamaindex-agents.md) — Data aur retrieval ke around bane agents. | 🟡 Intermediate | ~12 min |
| 11.8 | [Pydantic AI](./11.8-pydantic-ai.md) — Type-safe agents jinke inputs aur outputs validate hote hain. | 🟡 Intermediate | ~12 min |
| 11.9 | [Bina framework wala tarika](./11.9-the-no-framework-approach.md) — Kab provider SDK ke upar ek plain loop hi sabse sahi choice hai. | 🟡 Intermediate | ~10 min |
| 11.10 | [Framework kaise choose karo](./11.10-how-to-choose.md) — Aise sawal jo tumhe sahi tool tak le jaate hain. | 🟢 Beginner | ~8 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [10 · Multi-Agent Systems](../10-multi-agent-systems/README.md) ·
▶️ **Padhna shuru karo:** [11.1 Frameworks ka poora naksha](./11.1-framework-landscape.md) ·
➡️ **Agla chapter:** [12 · Evaluation](../12-evaluation/README.md)
