# 🧾 Cheatsheet

In notes ka har core idea ek hi page par. Har row us page se link karti hai jahan woh idea achhe se samjhaya gaya hai. Koi naya word dikha? [Glossary](GLOSSARY.md) dekho.

📑 **Is page par**

- [Core idea](#-core-idea)
- [Agent loop 15 lines mein](#-agent-loop-15-lines-mein)
- [Kitni autonomy deni hai, kaise chuno](#-kitni-autonomy-deni-hai-kaise-chuno)
- [Patterns ek nazar mein](#-patterns-ek-nazar-mein)
- [Tools checklist](#-tools-checklist)
- [Memory aur retrieval](#-memory-aur-retrieval)
- [Stopping aur error handling](#-stopping-aur-error-handling)
- [Evaluation](#-evaluation)
- [Safety checklist](#-safety-checklist)
- [Production aur cost](#-production-aur-cost)

## 🧠 Core idea

> **Agent ek LLM hai jo action chunta hai, result dekhta hai aur phir se chunta hai. Yeh loop tab tak chalta hai jab tak goal poora na ho jaye.**

| Part | Yeh kya hai | Padho |
| --- | --- | --- |
| ① Model | Woh LLM jo context padhta hai aur agla step decide karta hai | [1.4](docs/01-foundations/01.4-how-llms-work.md) |
| ② Instructions | Role, goal, rules: yaani system prompt | [1.5](docs/01-foundations/01.5-anatomy-of-an-agent.md) |
| ③ Tools | Functions jinhe chalane ke liye model tumhare code se *keh* sakta hai | [3.1](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md) |
| ④ Memory | Short-term (yeh conversation) aur long-term (runs ke beech store) | [5.1](docs/05-memory/05.1-short-term-vs-long-term-memory.md) |
| ⑤ Loop | Think → act → observe, limits ke saath | [2.1](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md) |

**LLM ki woh baatein jin par har agent tika hai** ([1.4](docs/01-foundations/01.4-how-llms-work.md)): API stateless hai (har call mein history dobara bhejo). Sab kuch (instructions, history, tools, results aur reply) context window mein fit hona chahiye. Paisa har token ka lagta hai. Stop reason check karo. Outputs har run mein badal sakte hain.

## 🔁 Agent loop 15 lines mein

```python
# llm: koi bhi chat client; user() aur tool_result() bas message dicts banate hain
def run(llm, goal, tools, specs, system, max_steps=10):
    messages = [user(goal)]
    for _ in range(max_steps):                          # loop par hamesha cap lagao
        reply = llm.chat(messages, system=system, tools=specs)
        messages.append(reply.to_message())
        if reply.stop_reason == "max_tokens":
            return "Stopped: reply was cut off."        # aadhe likhe tool calls mat chalao
        if not reply.tool_calls:
            return reply.text                           # model ne decide kiya ki kaam ho gaya
        for call in reply.tool_calls:                   # saare results ek saath wapas jaate hain
            try:
                messages.append(tool_result(call.id, tools[call.name](**call.arguments)))
            except Exception as exc:                    # errors information hain, crash nahi
                messages.append(tool_result(call.id, f"Error: {exc}", is_error=True))
    return "Stopped: step limit reached."
```

Ise step by step [2.3](docs/02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md) mein banao.

## 🎚 Kitni autonomy deni hai, kaise chuno

| Level | Naam | Model kya decide karta hai… | Kab use karo |
| --- | --- | --- | --- |
| 0 | Single prompt | sirf words | Language ka ek step wala kaam |
| 1 | Fixed workflow | har fixed step par words | Steps pehle se pata hain |
| 2 | Router | kaun si branch leni hai | Inputs clear categories mein bat jaate hain |
| 3 | Tool call | kaun sa function aur arguments, ek baar | Har request par ek lookup ya action |
| 4 | Agent loop | aage kya karna hai aur kab rukna hai | Raasta is par depend karta hai ki use kya milta hai |
| 5 | Autonomous | apne sub-goals, lambe time tak | Value saabit ho chuki ho, strong guardrails, human review |

**Rule:** sabse neecha level chuno jo problem solve kar de: code → ek call → workflow → agent ([1.3](docs/01-foundations/01.3-the-autonomy-spectrum.md), [1.6](docs/01-foundations/01.6-when-not-to-use-an-agent.md)). Chain ka har step bahut reliable hona chahiye. 10 steps mein har step 95% sahi ho, to overall sirf ~60% bachta hai.

## 🧩 Patterns ek nazar mein

| Pattern | Shape | Kab use karo | Padho |
| --- | --- | --- | --- |
| ReAct | Reason → act → observe, baar-baar | General agent loop | [2.2](docs/02-the-agent-loop/02.2-react-explained.md) |
| Prompt chaining | Calls ka fixed sequence, beech mein checks | Task saaf-saaf steps mein bat jaata hai | [9.1](docs/09-agent-design-patterns/09.1-prompt-chaining.md) |
| Routing | Classify karo, phir specialist path par bhejo | Alag type ke inputs ko alag handling chahiye | [9.2](docs/09-agent-design-patterns/09.2-routing.md) |
| Parallelisation | Independent calls ek saath; jodo (sectioning) ya vote karo | Speed, ya kai attempts se zyada bharosa | [9.3](docs/09-agent-design-patterns/09.3-parallelisation.md) |
| Orchestrator–workers | Lead model chalte-chalte workers ke liye sub-tasks banata hai | Sub-tasks pehle se pata nahi ho sakte | [9.4](docs/09-agent-design-patterns/09.4-orchestrator-workers.md) |
| Evaluator–optimizer | Banao, criteria par grade karo, sudhaaro | Quality criteria clear hain; iteration se fayda hai | [8.2](docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md), [9.5](docs/09-agent-design-patterns/09.5-evaluator-optimizer.md) |
| Reflection | Draft → khud critique → sudhaaro | Sasta improvement; external signals ke saath best | [8.1](docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md) |
| Self-critique with tests | Asli checks chalao, failures wapas do | Code ya koi bhi cheez jo verify ho sake | [8.3](docs/08-reflection-and-self-correction/08.3-self-critique-with-tests.md) |
| Plan-and-execute | Plan likho, phir uske steps chalao | Lambe tasks jinhe structure se fayda ho | [7.2](docs/07-planning-and-reasoning/07.2-plan-and-execute.md) |
| Human-in-the-loop | Ruko taaki insaan approve ya decide kare | Risky ya wapas na ho sakne wale actions | [9.6](docs/09-agent-design-patterns/09.6-human-in-the-loop.md) |
| Agentic RAG | Retrieval ek tool hai jo agent zaroorat par call karta hai | Tumhare apne documents par sawal | [6.4](docs/06-rag-for-agents/06.4-agentic-rag.md) |
| Supervisor | Manager agent specialist agents ko kaam deta hai | Alag skills ya tool sets | [10.2](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md) |
| Handoffs | Agents ek dusre ko control pass karte hain | Conversation ek domain se dusre mein jaati hai | [10.3](docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md) |

Pakka nahi pata? [9.7 Sahi pattern kaise chuno](docs/09-agent-design-patterns/09.7-choosing-a-pattern.md) ka decision flowchart use karo.

## 🔧 Tools checklist

- [ ] **Clear naam aur description** jo bataye ki tool kya karta hai, kab use karna hai aur kya lautata hai ([3.4](docs/03-tools-and-function-calling/03.4-designing-good-tools.md))
- [ ] **JSON Schema** jisme types, required fields, enums aur har field ki description ho ([3.2](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md))
- [ ] **Arguments validate karo** chalane se pehle; aisa helpful error lautao jis par model kuch kar sake
- [ ] **Chhota output**: kaam ke results, truncate ya paginate kiye hue
- [ ] **Kam tools**: har tool context khaata hai aur galat chunne ka ek aur mauka deta hai
- [ ] **Parallel calls**: unhe ek saath chalao; saare results ek message mein lautao ([3.5](docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md))
- [ ] **Least privilege**: default read-only; risky actions ko approval chahiye ([13.3](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md))
- [ ] **MCP se apps ke beech share karo** jab kai hosts ko same tools chahiye ([4.1](docs/04-model-context-protocol/04.1-why-mcp-exists.md))

## 🗃 Memory aur retrieval

| Zaroorat | Technique | Padho |
| --- | --- | --- |
| Lambi conversation context limit tak pahunch gayi | Purane turns ko trim, summarise ya compact karo | [5.2](docs/05-memory/05.2-summarisation-and-context-compaction.md) |
| Purane facts matlab ke basis par yaad karo | Vector memory: embed karo, store karo, similarity se search karo | [5.3](docs/05-memory/05.3-vector-memory.md) |
| Alag-alag kism ka knowledge | Episodic (kya hua), semantic (facts), procedural (kaise karna hai) | [5.4](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md) |
| Apne documents se jawab do | RAG: chunk → embed → retrieve → citations ke saath generate | [6.1](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md) |
| Behtar retrieval quality | Achhi chunking, hybrid search, re-ranking; recall@k naapo | [6.3](docs/06-rag-for-agents/06.3-chunking-strategies.md), [6.5](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md) |

## 🛑 Stopping aur error handling

**Hamesha ruko jab:** final answer aa jaye · step limit · time limit · token ya dollar budget · baar-baar same calls · `max_tokens` truncation · refusal ([2.4](docs/02-the-agent-loop/02.4-stopping-conditions.md), [16.5](docs/16-cost-and-performance/16.5-budget-limits-per-run.md)).

**Sambhalo, crash mat karo** ([2.5](docs/02-the-agent-loop/02.5-handling-errors-in-the-loop.md)): tool exceptions → aisa error result jo model padh sake · invalid arguments → validation message · unknown tool → valid names ki list do · rate limits aur server errors → backoff ke saath retry · baar-baar failure → fallback karo ya insaan ko saunp do ([15.5](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)).

## 📏 Evaluation

| Measure | Kis sawal ka jawab deta hai | Padho |
| --- | --- | --- |
| Task success | Kya woh sahi final state ya answer tak pahuncha? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| Trajectory | Kya usne samajhdaar raasta liya? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| Tool use | Sahi tools, sahi arguments, koi bekaar call nahi? | [12.2](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md) |
| LLM-as-judge | Quality jahan koi exact answer nahi hai (judge ko human labels se check karo) | [12.3](docs/12-evaluation/12.3-llm-as-judge.md) |
| Cost aur latency | Har poore task ke tokens, dollars aur seconds | [16.1](docs/16-cost-and-performance/16.1-token-cost-maths.md) |

Asli usage aur edge cases se dataset banao ([12.4](docs/12-evaluation/12.4-building-an-eval-dataset.md)). Har pull request par offline tests chalao, aur schedule par live evals ([12.5](docs/12-evaluation/12.5-regression-testing-in-ci.md)).

## 🛡 Safety checklist

- [ ] Threat model likha hua ho: kaun sa data, kaun se actions, kaun attack kar sakta hai, kin inputs ke through ([13.1](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md))
- [ ] Saare tool results, web pages aur documents ko **untrusted** maano: unme prompt injections ho sakte hain ([13.2](docs/13-safety-and-guardrails/13.2-prompt-injection.md))
- [ ] Ek hi agent mein private data + untrusted content + data bahar bhejne ka tarika, teeno ek saath mat do
- [ ] Least-privilege credentials; code execution sandbox mein; network access restrict karo ([13.3](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md))
- [ ] Input aur output guardrails: validation, PII checks, schema checks ([13.4](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md))
- [ ] Wapas na ho sakne wale ya bade asar wale actions ke liye human approval ([13.5](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md))
- [ ] Prompts ya logs mein koi secrets nahi; PII redact karo ([13.6](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md))

## 🚀 Production aur cost

| Concern | Yeh karo | Padho |
| --- | --- | --- |
| Kya hua, dekhna hai | Har run trace karo: model calls aur tool calls spans ke roop mein | [14.1](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md) |
| Debug | Reproduce karo → trace padho → failing part dhoondho → fix karo → test jodo | [14.5](docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md) |
| Lambe tasks | Background mein chalao; progress poll ya stream karo | [15.2](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md) |
| Retries | Side effect wale tools par idempotency keys | [15.3](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md) |
| Crashes | Har step ke baad state checkpoint karo; resume karo | [15.4](docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md) |
| Cost | Cost ≈ saare steps par Σ (input tokens × input price + output tokens × output price); input har step badhta hai | [16.1](docs/16-cost-and-performance/16.1-token-cost-maths.md) |
| Baar-baar wala context | Prompt caching: stable prefix pehle (tools → system → history) | [16.2](docs/16-cost-and-performance/16.2-prompt-caching.md) |
| Aasan vs mushkil requests | Chhote ya bade models par route karo, ya effort kam karo | [16.3](docs/16-cost-and-performance/16.3-model-routing.md) |
| Speed | Stream karo, tools parallel chalao, kam steps lo, cache karo | [16.4](docs/16-cost-and-performance/16.4-latency-optimisation.md) |

---

⬅️ **Wapas jao:** [Home](README.md) · 📖 [Glossary](GLOSSARY.md) · 🗺 [Roadmap](ROADMAP.md)
