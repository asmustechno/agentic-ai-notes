🏠 [Home](../../README.md) › 10 · Multi-Agent Systems

# 10 · Multi-Agent Systems

> **Padhne ka time:** ~54 min · **Level:** 🟡 Intermediate se 🔴 Advanced · **Pehle padho:** [02 · The Agent Loop](../02-the-agent-loop/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md), [09 · Agent Design Patterns](../09-agent-design-patterns/README.md)

Kabhi-kabhi ek agent kaafi nahi hota. Task ek context ke liye bahut bada hota hai, ya uske hisse specialists parallel mein better kar sakte hain. Yeh chapter dikhata hai ki agents ki teams kaise organise hoti hain (supervisors, handoffs aur shared state). Yeh bhi ki alag-alag organisations ke independent agents A2A jaise open protocols se kaise baat karte hain. Aur utna hi zaroori: kab agents ki team ek achhe agent se zyada mehengi padti hai aur bura kaam karti hai.

## 🎯 Is chapter mein kya seekhoge

- Kaam ko agents mein baantne se kya milta hai: separation of concerns, parallel exploration, context isolation aur specialised tools
- Supervisor pattern: ek lead agent jo tools ki tarah exposed specialist agents ko kaam delegate karta hai, aur achha brief kaise likhein
- Handoffs: conversation ka control ek agent se dusre ko dena, jaise OpenAI Agents SDK mein
- Agents messages ya shared blackboard se information kaise share karte hain, aur unhe ek dusre ka kaam overwrite karne se kaise rokein
- A2A protocol: Agent Cards, tasks, messages aur artifacts, aur A2A ka MCP se kya rishta hai
- Multi-agent systems ki keematein aur failure modes, aur ek checklist jo batati hai ki inhe kab use nahi karna

## 📋 Pehle se kya aana chahiye

- [1.5 Agent ke andar kya-kya hota hai](../01-foundations/01.5-anatomy-of-an-agent.md): team ka har agent ek normal agent hi hai
- [3.3 Function calling kaise kaam karta hai](../03-tools-and-function-calling/03.3-how-function-calling-works.md): agents tools ke through ek dusre ko call karte hain
- [9.4 Orchestrator–workers](../09-agent-design-patterns/09.4-orchestrator-workers.md): woh workflow jisse supervisor pattern nikalta hai
- 10.5 ke liye helpful: [4.1 MCP kyun bana?](../04-model-context-protocol/04.1-why-mcp-exists.md)

## 👀 Chapter ek nazar mein

![Agents ko arrange karne ke chaar tarike. Ek agent: agent apne tools call karta hai. Supervisor: supervisor do specialists ko briefs bhejta hai aur reports wapas paata hai. Handoffs: triage control billing ya tech ko transfer karta hai, jo ek dusre ko bhi transfer kar sakte hain. Shared state: do agents versioned keys wale shared blackboard ko padhte aur likhte hain.](../../assets/diagrams/10-multi-agent-topologies.svg)

*Left se shuru karo aur right tabhi jao jab zaroori ho. Pages 10.2, 10.3 aur 10.4 panels ②, ③ aur ④ cover karte hain. Page 10.5 organisations ke paar agents ko jodta hai, aur 10.6 samjhata hai ki aksar panel ① hi sahi jawab kyun hota hai.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 10.1 | [Multiple agents kyun?](./10.1-why-multiple-agents.md) — Kaam ko agents mein baantne se tumhe kya milta hai. | 🟡 Intermediate | ~8 min |
| 10.2 | [Supervisor aur hierarchical](./10.2-supervisor-and-hierarchical.md) — Ek manager agent specialist agents ko direct karta hai. | 🟡 Intermediate | ~10 min |
| 10.3 | [Peer-to-peer aur handoffs](./10.3-peer-to-peer-and-handoffs.md) — Agents seedha ek dusre ko control pass karte hain. | 🟡 Intermediate | ~10 min |
| 10.4 | [Shared state aur communication](./10.4-shared-state-and-communication.md) — Agents ek dusre ke kaam par pair rakhe bina apni jaankari kaise share karte hain. | 🔴 Advanced | ~10 min |
| 10.5 | [Agent-to-agent protocols](./10.5-agent-to-agent-protocols.md) — A2A jaise open protocols ka overview. | 🔴 Advanced | ~8 min |
| 10.6 | [Jab multi-agent cheezein aur bigaad deta hai](./10.6-when-multi-agent-makes-things-worse.md) — Cost, latency aur coordination failures jin par nazar rakhni hai. | 🔴 Advanced | ~8 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [09 · Agent Design Patterns](../09-agent-design-patterns/README.md) ·
▶️ **Padhna shuru karo:** [10.1 Multiple agents kyun?](./10.1-why-multiple-agents.md) ·
➡️ **Agla chapter:** [11 · Frameworks](../11-frameworks/README.md)
