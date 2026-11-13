🏠 [Home](../../README.md) › 05 · Memory

# 05 · Memory

> **Padhne ka time:** ~48 min · **Level:** 🟢 Beginner se 🔴 Advanced · **Pehle padho:** [01 · Foundations](../01-foundations/README.md), [02 · The Agent Loop](../02-the-agent-loop/README.md)

Model do calls ke beech kuch yaad nahi rakhta. Agent current task ke baare mein jo bhi "jaanta" hai, aur pichhle hafte ke user ke baare mein jo bhi, woh sab tumhare code ko wapas context mein daalna padta hai. Yeh chapter isi kaam ko achhe se karne ke baare mein hai.

Yeh short-term memory (context window) ko long-term memory (jo tum model ke bahar store karte ho) se alag karta hai. Phir dikhata hai ki trimming, summarisation aur provider-side compaction se lambe runs ko budget ke andar kaise rakhein. Phir ek vector memory banata hai jo similarity se recall karti hai, aur long-term memory ko episodic, semantic aur procedural kinds mein baantta hai. Aakhir mein woh design decisions aate hain jo memory ko creepy ki jagah helpful banate hain: kya store karna hai, kab recall karna hai, staleness, privacy, cost aur evaluation.

## 🎯 Is chapter mein kya seekhoge

- Short-term memory (context window) aur long-term memory mein farak, aur write, store, recall, inject wala cycle
- Lambi conversation ko budget ke andar rakhne ke teen tarike: trimming, rolling summaries aur purane tool results clear karna
- Anthropic ka server-side compaction aur context editing, aur OpenAI ka Responses API compaction kaise kaam karta hai
- Vector memory embeddings kaise store karti hai aur cosine similarity se kaise recall karti hai, aur asli systems ko embedding model kyun chahiye
- Episodic, semantic aur procedural memory (CoALA paper se), aur Anthropic ka memory tool
- Trade-offs: kya store karna hai, kab likhna aur recall karna hai, staleness, privacy aur PII, cost aur evaluation

## 📋 Pehle se kya aana chahiye

- [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](../01-foundations/01.4-how-llms-work.md): tokens, context windows aur statelessness
- [1.5 Agent ke andar kya-kya hota hai](../01-foundations/01.5-anatomy-of-an-agent.md): memory, paanch parts mein se ek ke roop mein
- [2.3 50 lines mein agent, bilkul zero se](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md): woh loop jis par in pages ka code banta hai
- [0.3 Setup](../00-start-here/00.3-setup.md), taaki tum code snippets chala sako

## 👀 Chapter ek nazar mein

![Beech mein context window hai jismein instructions, recall ki hui memories, purane turns ki summary aur recent turns hain; model har call par yeh sab padhta hai. Left se purane turns summarise hoke isme aate hain. Right mein long-term memory hai jismein semantic facts, episodic past runs, procedural rules aur ek vector index hain; memories context mein recall hoti hain aur wapas bahar likhi jaati hain.](../../assets/diagrams/05-memory-map.svg)

*Page 5.1 is picture ke dono hisse samjhata hai. Page 5.2 left wala "summarise" arrow hai. Pages 5.3 aur 5.4 right wale long-term stores hain, aur 5.5 unke beech ke "recall" aur "write" arrows ke baare mein hai.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 5.1 | [Short-term vs long-term memory](./05.1-short-term-vs-long-term-memory.md) — Context window versus woh memory jo conversation ke baad bhi bachi rehti hai. | 🟢 Beginner | ~8 min |
| 5.2 | [Summarisation aur context compaction](./05.2-summarisation-and-context-compaction.md) — Lambe runs ko context window ke andar rakho. | 🟡 Intermediate | ~10 min |
| 5.3 | [Vector memory](./05.3-vector-memory.md) — Memories ko keywords se nahi, matlab se store aur recall karo. | 🟡 Intermediate | ~10 min |
| 5.4 | [Episodic, semantic aur procedural memory](./05.4-episodic-semantic-and-procedural-memory.md) — Long-term memory ki teen kinds, aur har ek kis kaam ki hai. | 🟡 Intermediate | ~10 min |
| 5.5 | [Memory design ke trade-offs](./05.5-memory-design-trade-offs.md) — Kya store karna hai, kab recall karna hai, aur iska cost kya hai. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [04 · Model Context Protocol (MCP)](../04-model-context-protocol/README.md) ·
▶️ **Padhna shuru karo:** [5.1 Short-term vs long-term memory](./05.1-short-term-vs-long-term-memory.md) ·
➡️ **Agla chapter:** [06 · RAG for Agents](../06-rag-for-agents/README.md)
