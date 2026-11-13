🏠 [Home](../../README.md) › 13 · Safety & Guardrails

# 13 · Safety & Guardrails

> **Padhne ka time:** ~65 min · **Level:** 🟡 Intermediate se 🔴 Advanced · **Pehle padho:** [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md), [12 · Evaluation](../12-evaluation/README.md) (helpful hai)

Chatbot kuch galat bol de, toh sirf sharmindagi hoti hai. Lekin agent kuch galat *kar* de, toh woh tumhari customer list kisi anjaan ko bhej sakta hai, database delete kar sakta hai, ya galat bande ko refund de sakta hai.

Yeh chapter agent safety ko ek security problem ki tarah dekhta hai. Pehle samjho ki tum par kaun attack kar sakta hai aur kaise. Phir kai imperfect defences ek ke upar ek lagao, taaki koi ek failure disaster na ban jaaye.

Yeh chapter mushkil hisse ke baare mein honest hai. Prompt injection ka abhi tak koi complete fix nahi hai. Isliye zyada kaam is baat par hota hai ki agar agent bevakoof ban bhi jaaye, toh woh kya-kya *kar sakta* hai, usko limit karo.

## 🎯 Is chapter mein kya seekhoge

- Agent ka threat model kaise banate hain: assets, attackers, entry points, aur private data, untrusted content aur external communication ki "lethal trifecta"
- Direct aur indirect prompt injection, aur har defence (marking, taint tracking, dual-LLM pattern, CaMeL, human approval) kya rokta hai aur kya nahi rokta
- Tools ke liye least privilege: scoped credentials, read-only defaults, allowlists, network egress control aur sandboxes
- Layered input aur output guardrails kaise banao jo test karne mein aasaan hon
- Irreversible actions se pehle human ko kaise bithao, bina usko approvals mein dubaaye
- Secrets aur personal data ko prompts, logs aur outputs se bahar kaise rakho

## 📋 Pehle se kya aana chahiye

- [1.5 Agent ke andar kya-kya hota hai](../01-foundations/01.5-anatomy-of-an-agent.md): woh paanch parts jinko tum protect karoge
- [3.3 Function calling kaise kaam karta hai](../03-tools-and-function-calling/03.3-how-function-calling-works.md): model sirf *maangta* hai, tumhara code *chalata* hai; zyada tar defences isi gap mein rehte hain
- Basic Python, bas itna ki snippets padh sako (agar chalana hai toh [0.3 Setup](../00-start-here/00.3-setup.md) dekho)

## 👀 Chapter ek nazar mein

![Chhe defensive layers, chhedon wale slices ki tarah bane hue: input guardrails, untrusted content ki marking, least-privilege tools, human approval, sandbox aur egress control, aur redaction ke saath output guardrails. Ek attack ka arrow pehli teen layers ke chhedon se nikal jaata hai aur human approval par ruk jaata hai. Monitoring aur audit log har layer ke neeche chalte hain.](../../assets/diagrams/13-defence-in-depth.svg)

*Koi bhi layer perfect nahi hai. Yahan attack teen layers se bach nikalta hai aur chauthi par pakda jaata hai. Pages 13.2 se 13.6 har ek mein ek ya do layers banate hain; 13.1 tumhe decide karne mein madad karta hai ki tumhare agent ko kaun si layers chahiye.*

## 📄 Is chapter ke pages

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 13.1 | [Agents ke liye threat model](./13.1-threat-model-for-agents.md) — Jab model actions le sakta hai, toh kya-kya galat ho sakta hai. | 🟡 Intermediate | ~10 min |
| 13.2 | [Prompt injection aur uske defences](./13.2-prompt-injection.md) — Direct aur indirect injection, aur nuksaan ko limit kaise karo. | 🔴 Advanced | ~15 min |
| 13.3 | [Least-privilege tools aur sandboxing](./13.3-least-privilege-and-sandboxing.md) — Agents ko sirf utna access do jitna zaroori hai. | 🔴 Advanced | ~12 min |
| 13.4 | [Input aur output guardrails](./13.4-input-and-output-guardrails.md) — Jo andar jaata hai aur jo bahar aata hai, dono check karo. | 🟡 Intermediate | ~10 min |
| 13.5 | [Risky actions ke liye human approval](./13.5-human-approval-for-risky-actions.md) — Irreversible steps se pehle kisi insaan ka approval lo. | 🟡 Intermediate | ~8 min |
| 13.6 | [Secrets aur PII handling](./13.6-secrets-and-pii.md) — Keys aur personal data ko prompts, logs aur outputs se bahar rakho. | 🔴 Advanced | ~10 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Pichla chapter:** [12 · Evaluation](../12-evaluation/README.md) ·
▶️ **Padhna shuru karo:** [13.1 Agents ke liye threat model](./13.1-threat-model-for-agents.md) ·
➡️ **Agla chapter:** [14 · Observability & Debugging](../14-observability-and-debugging/README.md)
