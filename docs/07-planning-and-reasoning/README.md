🏠 [Home](../../README.md) › 07 · Planning & Reasoning

# 07 · Planning & Reasoning

> **Padhne ka time:** ~46 min · **Level:** 🟢 Beginner se 🔴 Advanced tak · **Pehle padho:** [02 · The Agent Loop](../02-the-agent-loop/README.md)

Ek ReAct agent ek waqt mein ek step decide karta hai. Chhote tasks ke liye itna kaafi hai. Lekin lambe tasks ko aur cheezein chahiye: kaam karne se pehle reasoning, ek plan jo bataye ki "done" ka matlab kya hai, aur plan jab reality se takraaye tab sambhalne ka tarika. Yeh chapter shuru hota hai is baat se ki models reason kaise karte hain (chain-of-thought prompting aur built-in extended thinking). Phir hum plan-and-execute agents banate hain, dekhte hain ki goal ko check karne layak sub-tasks mein kaise todte hain, tree-of-thoughts search ka overview lete hain, aur aakhir mein step fail hone pe re-planning sikhte hain.

## 🎯 Is chapter mein kya seekhoge

- Chain-of-thought prompting, Claude aur OpenAI models pe built-in thinking, aur reasoning effort kaise set karte hain
- Explicit "think step by step" prompting kab abhi bhi help karti hai, aur kab nahi
- Plan-and-execute pattern: ek planner, ek executor, aur code jo plan validate aur schedule karta hai
- Goal ko done criteria aur dependency graph ke saath sub-tasks mein kaise todte hain
- Tree of thoughts adhoore solutions ke upar kaise search karta hai, aur iski cost kya hai
- Fail hua step kaise pakdein, bacha kaam re-plan kaise karein, aur limits ke andar kaise rukein

## 📋 Pehle se kya aana chahiye

- [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](../01-foundations/01.4-how-llms-work.md): tokens aur output limits
- [2.2 ReAct ko samjho](../02-the-agent-loop/02.2-react-explained.md) aur [2.5 Loop mein errors kaise sambhalein](../02-the-agent-loop/02.5-handling-errors-in-the-loop.md)
- [3.3 Function calling kaise kaam karta hai](../03-tools-and-function-calling/03.3-how-function-calling-works.md)

## 👀 Chapter ek nazar mein

![Ek goal planner model ke paas jaata hai, jo steps ka plan likhta hai, dependencies aur done-when criteria ke saath. Tools wala ek executor ek waqt mein ek ready step chalata hai. Ek check agla step wapas executor ko bhejta hai, saare steps ho jaane pe user ko answer bhejta hai, ya agar koi step fail hua toh bache kaam ke liye re-planner se naye steps maangta hai.](../../assets/diagrams/07-plan-execute-replan.svg)

*Yeh woh loop hai jo yeh chapter banata hai. Planner aur re-planner sochte hain; executor kaam karta hai; tumhara code har result check karta hai aur decide karta hai ki aage kya hoga. Har model box kaam karne se pehle reason kar sakta hai (7.1).*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 7.1 | [Chain-of-thought aur extended thinking](./07.1-chain-of-thought-and-extended-thinking.md) — Step-by-step reasoning, prompting tricks se le kar model ki built-in thinking tak. | 🟢 Beginner | ~10 min |
| 7.2 | [Plan-and-execute](./07.2-plan-and-execute.md) — Pehle plan banao, phir usko step by step poora karo. | 🟡 Intermediate | ~10 min |
| 7.3 | [Task decomposition](./07.3-task-decomposition.md) — Bade goal ko chhote, check karne layak tasks mein todo. | 🟡 Intermediate | ~8 min |
| 7.4 | [Tree-of-thoughts (ek overview)](./07.4-tree-of-thoughts.md) — Reasoning ki kai lines explore karo aur best wali rakho. | 🔴 Advanced | ~8 min |
| 7.5 | [Jab kuch fail ho, tab re-planning](./07.5-re-planning-when-things-fail.md) — Toota hua plan pehchano aur raasta badlo. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [06 · RAG for Agents](../06-rag-for-agents/README.md) ·
▶️ **Padhna shuru karo:** [7.1 Chain-of-thought aur extended thinking](./07.1-chain-of-thought-and-extended-thinking.md) ·
➡️ **Agla chapter:** [08 · Reflection & Self-Correction](../08-reflection-and-self-correction/README.md)
