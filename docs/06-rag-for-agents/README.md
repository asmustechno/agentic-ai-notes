🏠 [Home](../../README.md) › 06 · RAG for Agents

# 06 · RAG for Agents

> **Padhne ka time:** ~49 min · **Level:** 🟢 Beginner se 🔴 Advanced tak · **Pehle padho:** [01 · Foundations](../01-foundations/README.md), [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md)

Models sirf utna jaante hain jitna un par train hua aur jitna tum prompt mein daalte ho. Retrieval-augmented generation (RAG) *tumhare* documents ke sahi tukde prompt mein daalta hai. Isse jawab tumhare facts par tike rehte hain aur unhe cite bhi kar sakte hain.

Yeh chapter basic "pehle retrieve, phir generate" idea se shuru hota hai. Phir embeddings, vector databases aur chunking se hote hue agentic RAG tak jaata hai, jahan agent khud decide karta hai ki kab aur kya search karna hai. Aakhir mein dekhte hain ki retrieval ko behtar kaise karein aur measure kaise karein.

## 🎯 Is chapter mein kya seekhoge

- RAG kya hai, aur RAG ki zyadatar failures asal mein retrieval failures kyun hoti hain
- Embeddings kya hain, cosine similarity aur ANN indexes kaise kaam karte hain, aur vector store kaise chunein
- Documents ko chunk karne ke paanch tarike, aur ek galat cut kaise confident galat jawab deta hai
- Retrieval ko tool kaise banayein, taaki agent queries rewrite kar sake, ek se zyada baar search kare, aur "not found" bol sake
- Reciprocal rank fusion ke saath hybrid search (BM25 + vectors), aur cross-encoders se re-ranking
- Labelled eval set par recall@k, precision@k, MRR aur nDCG se retrieval kaise measure karein

## 📋 Pehle se kya aana chahiye

- [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](../01-foundations/01.4-how-llms-work.md): tokens aur context windows
- [1.5 Agent ke andar kya-kya hota hai](../01-foundations/01.5-anatomy-of-an-agent.md): model, tools, memory aur loop
- [3.3 Function calling kaise kaam karta hai](../03-tools-and-function-calling/03.3-how-function-calling-works.md), agentic RAG (6.4) ke liye
- Kaam ka hai lekin zaroori nahi: [5.3 Vector memory](../05-memory/05.3-vector-memory.md)

## 👀 Chapter ek nazar mein

![Do lanes. Pehle se, documents ko chunk, embed karke ek vector index aur ek keyword index mein store kiya jaata hai. Sawal ke time user ka sawal ek agent ke paas jaata hai. Agent ek search_docs tool call karta hai jo index par hybrid search aur re-ranking chalata hai. Agent results padhta hai, shayad dobara search karta hai, aur citations ke saath jawab deta hai ya "not found" bolta hai.](../../assets/diagrams/06-rag-pipeline.svg)

*Indexing (upar) har document ke liye ek baar hoti hai. Retrieval (neeche) har sawal par hota hai. Har box par us page ka label hai jo use cover karta hai. Agentic RAG mein agent user aur search tool ke beech baitha hai, isliye woh zero, ek ya kai baar search kar sakta hai.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 6.1 | [RAG, 5 minute mein](./06.1-rag-in-5-minutes.md) — Pehle retrieve, phir generate: poora idea paanch minute mein. | 🟢 Beginner | ~5 min |
| 6.2 | [Embeddings aur vector databases](./06.2-embeddings-and-vector-databases.md) — Text kaise aise numbers banta hai jinhe search kar sako. | 🟢 Beginner | ~10 min |
| 6.3 | [Chunking ke tarike](./06.3-chunking-strategies.md) — Documents ko kaise todein taaki retrieval sahi tukda dhoondhe. | 🟡 Intermediate | ~10 min |
| 6.4 | [Agentic RAG](./06.4-agentic-rag.md) — Agent khud decide karta hai ki kab, kya aur kaise retrieve karna hai. | 🟡 Intermediate | ~12 min |
| 6.5 | [Re-ranking aur retrieval evaluation](./06.5-re-ranking-and-retrieval-evaluation.md) — Jo retrieve karte ho, uski quality behtar karo aur measure karo. | 🔴 Advanced | ~12 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [05 · Memory](../05-memory/README.md) ·
▶️ **Padhna shuru karo:** [6.1 RAG, 5 minute mein](./06.1-rag-in-5-minutes.md) ·
➡️ **Agla chapter:** [07 · Planning & Reasoning](../07-planning-and-reasoning/README.md)
