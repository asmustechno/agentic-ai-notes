🏠 [Home](../../README.md) › 15 · Production & Deployment

# 15 · Production & Deployment

> **Padhne ka time:** ~69 min · **Level:** 🔴 Advanced · **Pehle padho:** [02 · The Agent Loop](../02-the-agent-loop/README.md), [14 · Observability & Debugging](../14-observability-and-debugging/README.md)

Laptop par chalta hua agent banana aasaan wala half hai. Yeh chapter doosra half cover karta hai. Agent loop ke around kya-kya hona chahiye taaki woh tab bhi chale jab bahut saare users ek saath aa jayein, provider overloaded ho, koi deploy run ko beech mein maar de, ya koi retry same email do baar bhejne ki koshish kare.

Is chapter mein tum production agent ka architecture dekhoge. Synchronous aur background runs ke beech choose karna seekhoge. Idempotency keys se retries ko safe banaoge. Runs ko checkpoint karoge taaki crash ke baad woh resume ho sakein. Fallbacks aur circuit breakers se rate limits aur outages jhel paoge. Aur aakhir mein agent ko ek tested FastAPI service ke roop mein Docker container mein ship karoge.

## 🎯 Is chapter mein kya seekhoge

- Loop ke around kaun se components hote hain (API layer, job queue, workers, state store, model gateway, guardrails, observability, evals) aur har ek ki zaroorat kab padti hai
- Kab ek hi request ke andar jawab dena hai, kab stream karna hai, aur kab run id return karke background mein kaam karna hai
- Kaun se errors retry karne hain, jitter ke saath back off kaise karna hai, aur idempotency keys aur dead-letter queues duplicate side effects kaise rokti hain
- Agent run ko SQLite mein checkpoint kaise karna hai aur crash ke baad bina kaam repeat kiye resume kaise karna hai
- Rate limits kaise handle karne hain, doosre model ya provider par fall back kaise karna hai, circuit breaker kaise use karna hai; aur Anthropic ka server-side refusal fallback kya karta hai aur kya nahi karta
- Agent ko FastAPI se serve kaise karna hai, `TestClient` aur ek scripted fake model se test kaise karna hai, aur use secure Docker image mein package kaise karna hai

## 📋 Pehle se kya aana chahiye

- [2.3 50 lines mein agent, bilkul zero se](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md) aur [2.5 Loop mein errors kaise sambhalein](../02-the-agent-loop/02.5-handling-errors-in-the-loop.md): yahi loop hai jise yeh chapter wrap karta hai
- [14.1 Agent runs ko trace karna](../14-observability-and-debugging/14.1-tracing-agent-runs.md): observability wale parts ke liye kaam aayega
- Basic HTTP (status codes, headers) aur command line ki thodi jaankari. Docker optional hai: tum har page bina Docker ke bhi follow kar sakte ho

## 👀 Chapter ek nazar mein

![Production agent ka architecture: client ek API layer ko call karta hai, jo chhote tasks ka jawab seedha deti hai ya lambe tasks ko queue mein daal deti hai. Workers agent loop chalate hain, primary aur fallback providers wale gateway ke through models ko call karte hain, tool services call karte hain, aur har step ko state store mein checkpoint karte hain. Guardrails loop ko check karte hain; observability aur evals sab kuch cover karte hain.](../../assets/diagrams/15-production-architecture.svg)

*Agent loop beech wala chhota sa box hai. Page 15.1 poori picture samjhata hai; 15.2 API layer ka sync-ya-async wala choice; 15.3 queue aur safe retries; 15.4 state store; 15.5 model gateway; aur 15.6 service ko deploy ke liye package karta hai.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 15.1 | [Production agent ka architecture](./15.1-production-architecture.md) — Loop ke around woh components jo use reliable banate hain. | 🔴 Advanced | ~12 min |
| 15.2 | [Sync vs async aur background agents](./15.2-sync-vs-async-agents.md) — Request-response agents vs lambe chalne wale jobs. | 🔴 Advanced | ~10 min |
| 15.3 | [Queues, retries aur idempotency](./15.3-queues-retries-and-idempotency.md) — Safely retry karo, bina koi kaam do baar kiye. | 🔴 Advanced | ~12 min |
| 15.4 | [State persistence aur resumability](./15.4-state-persistence-and-resumability.md) — Progress save karo taaki crash ke baad run resume ho sake. | 🔴 Advanced | ~10 min |
| 15.5 | [Rate limits aur fallbacks](./15.5-rate-limits-and-fallbacks.md) — Provider slow, busy ya down ho, tab bhi chalte raho. | 🔴 Advanced | ~10 min |
| 15.6 | [FastAPI aur Docker se deploy karna](./15.6-deploying-with-fastapi-and-docker.md) — Agent ko containerised web service ke roop mein ship karo. | 🔴 Advanced | ~15 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [14 · Observability & Debugging](../14-observability-and-debugging/README.md) ·
▶️ **Padhna shuru karo:** [15.1 Production agent ka architecture](./15.1-production-architecture.md) ·
➡️ **Agla chapter:** [16 · Cost & Performance](../16-cost-and-performance/README.md)
