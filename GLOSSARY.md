# 📖 Glossary

In notes mein jo bhi term use hua hai, sab yahan A se Z tak hai. Har entry mein ek chhoti, simple definition hai. Saath mein us page ka link hai jahan woh term achhe se samjhaya gaya hai. Pages pehli baar koi term use karte hain to yahin link karte hain.

> Koi term missing hai? [Suggest karo](.github/ISSUE_TEMPLATE/suggest-topic.md).

**Seedha jao:** [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [V](#v) · [W](#w)

## A

### Agent

Aisa system jisme ek [large language model](#large-language-model-llm) step by step decide karta hai ki goal tak pahunchne ke liye kaun sa action lena hai. Aksar yeh action [tools](#tool) call karna hota hai. Woh tab tak chalta rehta hai jab tak goal poora na ho jaye ya woh ruk na jaye. → [1.1 AI agent kya hai?](docs/01-foundations/01.1-what-is-an-ai-agent.md)

### Agent card

A2A mein ek JSON document jo agent publish karta hai (aksar /.well-known/agent-card.json par). Isme agent ka naam, skills, endpoints, capabilities aur authentication ki zaroorat likhi hoti hai. → [10.5 Agent-to-agent protocols](docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md)

### Agent framework

Ek library jo agent banane ke ready-made pieces deti hai, jaise loop, tool schemas, memory aur multi-agent patterns. Isse tumhe yeh code khud kam likhna padta hai. → [11.1 Frameworks ka poora naksha](docs/11-frameworks/11.1-framework-landscape.md)

### Agent harness

Ek poora, ready-made agent runtime jisme tools, permissions aur context management pehle se built-in hote hain. Tum ise banate nahi, sirf configure karte ho. Claude Code, jo Claude Agent SDK ke through use hota hai, aisa hi ek harness hai. → [11.6 Claude Agent SDK](docs/11-frameworks/11.6-claude-agent-sdk.md)

### Agent loop

Agent ke beech ka repeat hone wala cycle: current state dekho, socho kya karna hai, act karo (jaise koi tool call karo), phir result dekho. → [2.1 Observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

### Agent-computer interface (ACI)

Commands aur tools ka woh set jisse agent computer environment mein kaam karta hai. Jaise coding agent ke liye search, view aur edit commands. Iska design agent ki performance par bahut asar daalta hai. → [17.1 Coding agent](docs/17-case-studies/17.1-coding-agent.md)

### Agent2Agent protocol (A2A)

Linux Foundation ke under ek open protocol. Isse alag-alag agents Agent Cards ke through ek dusre ko dhoondh sakte hain, messages bhej sakte hain aur shared tasks track kar sakte hain. Apne andar ki details expose nahi karni padti. → [10.5 Agent-to-agent protocols](docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md)

### Agentic RAG

Retrieval-augmented generation jisme search ek tool hai jo model khud call karta hai. Agent decide karta hai ki search karna hai ya nahi, kya search karna hai, dobara kab search karna hai, aur kab bolna hai ki answer mila hi nahi. → [6.4 Agentic RAG](docs/06-rag-for-agents/06.4-agentic-rag.md)

### API key

Ek secret string jo model provider ko batati hai ki tum kaun ho, aur tumhare code ko uski API call karne deti hai. Ise environment variable ya `.env` file mein rakho, code mein kabhi nahi. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Approval gate

Agent loop ka woh code jo risky tool call ko rok deta hai. Woh insaan ko exact preview dikhata hai ki kya hone wala hai, aur approve hone par hi chalata hai. → [13.5 Risky actions ke liye human approval](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md)

### Approximate nearest neighbour (ANN) search

Query ke sabse kareeb wale vectors dhoondhne ka tarika, bina har stored vector se compare kiye. Thodi accuracy jaati hai, lekin speed bahut badh jaati hai. HNSW aur IVF common ANN indexes hain. → [6.2 Embeddings aur vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### At-least-once delivery

Queue ki guarantee ki har job tab tak deliver hoti rahegi jab tak koi worker confirm na kare. Kuch bhi khota nahi, lekin kuch jobs ek se zyada baar process ho sakti hain. Isliye handlers aise hone chahiye ki do baar chalne par bhi safe rahein. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Audit log

Append-only record jisme agent ka har action likha hota hai, chahe hua ho ya refuse hua ho. Saath mein yeh bhi ki kisne approve kiya aur kya hua. Yeh investigation aur accountability ke liye rakha jaata hai. → [13.5 Risky actions ke liye human approval](docs/13-safety-and-guardrails/13.5-human-approval-for-risky-actions.md)

### Autonomy spectrum

Ek scale jo batata hai ki LLM system mein model kitna decide karta hai. Ek single prompt (sab kuch code decide karta hai) se lekar fully autonomous agent tak (model apne sub-goals khud set karta hai). → [1.3 Autonomy ka spectrum](docs/01-foundations/01.3-the-autonomy-spectrum.md)

## B

### Background agent

Aisa agent run jiska koi real time mein wait nahi kar raha. Yeh schedule ya kisi event se start hota hai, aur apna result kisi kaam ki jagah report karta hai, jaise ticket ya chat message. → [15.2 Sync vs async aur background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Benchmark

Tasks ka ek public, standard set jise grade karne ka tarika fixed hota hai. Iska use models ya agent systems compare karne ke liye hota hai. Score poore tested system (model plus scaffold) ke baare mein hai, aur sirf us benchmark ke tasks par. → [12.6 Public benchmarks (ek overview)](docs/12-evaluation/12.6-public-benchmarks.md)

### Blackboard

Ek shared store jise kai agents tools ke through padhte aur likhte hain. Isme rules chahiye ki kaun kya dekh aur badal sakta hai, aur conflicting writes kaise pakdein. → [10.4 Shared state aur communication](docs/10-multi-agent-systems/10.4-shared-state-and-communication.md)

### BM25

Keyword ranking function jo documents ko score karta hai is basis par ki usme query ke kitne words hain. Rare words ko zyada weight milta hai. Repeat words ka fayda dheere-dheere kam hota hai, aur document ki length ke liye correction hota hai. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

### Browser agent

Aisa agent jo tools ke through web browser use karta hai, jaise page kholna, text padhna, elements par click karna ya fill karna. Isse woh websites par tasks poore karta hai. → [3.7 Computer use aur browser agents](docs/03-tools-and-function-calling/03.7-computer-use-and-browser-agents.md)

## C

### Canary token

Ek unique, bematlab string jo system prompt ya secret document mein daal di jaati hai. Agar yeh kabhi model ke output mein dikhe, to samjho hidden text leak ho gaya. Tab output guardrail reply ko block kar sakta hai. → [18.5 Project 5: Production-ready support agent](docs/18-projects/18.5-project-5-production-support-agent.md)

### Chain-of-thought (CoT)

Model se final answer se pehle beech ke reasoning steps likhwana. Isse multi-step problems par accuracy badhti hai. Wei et al. (2022) ne introduce kiya. → [7.1 Chain-of-thought aur extended thinking](docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md)

### Chatbot

Aisa system jo har message par model ka ek hi reply deta hai aur koi action nahi leta. Woh sirf wahi use kar sakta hai jo model pehle se jaanta hai ya jo prompt mein hai. → [1.2 Chatbot, workflow aur agent mein farak](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

### Checkpoint

Run ki state ka saved snapshot (agent ke liye: messages aur step counter). Isse crash ke baad run wahin se resume ho sakta hai, shuru se nahi. → [15.4 State persistence aur resumability](docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md)

### Chunking

Retrieval ke liye index karne se pehle documents ko chhote pieces (chunks) mein todna. Tum kaise todte ho, usi se decide hota hai ki search kya dhoondh paayega. → [6.3 Chunking ke tarike](docs/06-rag-for-agents/06.3-chunking-strategies.md)

### Circuit breaker

Ek guard jo baar-baar fail hone par kisi dependency ko call karna band kar deta hai. Cool-down period tak turant fail karta hai, phir ek trial call jaane deta hai yeh dekhne ke liye ki woh theek hui ya nahi. → [15.5 Rate limits aur fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Compounding errors

Har step ki chhoti error rate bahut saare steps mein milkar badi ho jaati hai. Agar har step probability p se sahi hai, to saare n steps sahi hone ki probability pⁿ hai. Isi wajah se lambe agent runs ko galtiyan pakadne ke tarike chahiye. → [1.6 Agent kab use NAHI karna chahiye](docs/01-foundations/01.6-when-not-to-use-an-agent.md)

### Computer use

Model ko insaan ki tarah computer chalane dena. Model screenshots leta hai aur mouse/keyboard actions maangta hai, jo tumhara code ek isolated machine par karta hai. → [3.7 Computer use aur browser agents](docs/03-tools-and-function-calling/03.7-computer-use-and-browser-agents.md)

### Confused deputy

Ek attack jisme sahi authority wale program ko (jaise OAuth credentials rakhne wala MCP proxy server) bewakoof bana kar attacker ke liye woh authority use karwa li jaati hai. → [4.6 MCP servers ki security](docs/04-model-context-protocol/04.6-mcp-security.md)

### Container

Container image ka chalta hua instance. Yeh ek isolated process hai jiska apna filesystem hota hai, aur har machine par same tarike se start hota hai. → [15.6 FastAPI aur Docker se deploy karna](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Container image

Application, uske runtime aur dependencies ka packaged, read-only bundle (jaise Docker image). Ek baar build karo, kahin bhi chalao. Isme secrets kabhi nahi hone chahiye. → [15.6 FastAPI aur Docker se deploy karna](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Context compaction

Lambi conversation ko chhota karna taaki woh budget mein fit ho. Aksar purane turns ko summary se replace karte hain, aur model poori history ki jagah summary se aage badhta hai. Anthropic aur OpenAI yeh server-side bhi kar sakte hain. → [5.2 Summarisation aur context compaction](docs/05-memory/05.2-summarisation-and-context-compaction.md)

### Context editing

Model ke dekhne se pehle conversation se specific content hata dena, jaise purane tool results ya thinking blocks. Isse context chhota rehta hai, bina summary banaye. → [5.2 Summarisation aur context compaction](docs/05-memory/05.2-summarisation-and-context-compaction.md)

### Context isolation

Kisi sub-task ko apna fresh context dena. Uska raw kaam (searches, files, tool output) main agent ke context se bahar rehta hai, aur sirf chhota sa result wapas aata hai. → [10.1 Multiple agents kyun?](docs/10-multi-agent-systems/10.1-why-multiple-agents.md)

### Context window

Text ki maximum quantity, [tokens](#token) mein naapi hui, jo model ek request mein padh sakta hai. Current task ke baare mein model jo bhi "jaanta" hai, sab isi mein fit hona chahiye. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Correlation ID

Ek identifier, jaise run ID, jo ek request ya agent run ki har log line aur trace par lagaya jaata hai. Isse uske saare records dhoondh kar jode ja sakte hain. → [14.2 Tool calls ko log karna](docs/14-observability-and-debugging/14.2-logging-tool-calls.md)

### Cosine similarity

Yeh naapta hai ki do vectors kitna same direction mein point karte hain, -1 se 1 tak. Length 1 par scale kiye embeddings ke liye yeh unke dot product ke barabar hai. → [6.2 Embeddings aur vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

## D

### Data contamination

Jab benchmark ya test ke sawal (ya unke jawab) model ke training data mein pahunch jaate hain. Tab score kuch had tak ratta dikhata hai, aur nayi problems par model ko jitna achha batata hai utna woh hota nahi. → [12.6 Public benchmarks (ek overview)](docs/12-evaluation/12.6-public-benchmarks.md)

### Data exfiltration

Private data ko system se nikaal kar aisi jagah pahunchana jahan attacker padh sake. Jaise agent ko bewakoof bana kar data email karwana ya URL mein daalwana. → [13.1 Agents ke liye threat model](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Dead-letter queue (DLQ)

Un jobs ke liye holding queue jo hamesha ke liye fail ho gayi ya jinke retries khatam ho gaye. Na woh hamesha retry hoti hain, na chupchaap gayab hoti hain. Koi insaan unhe dekh kar replay kar sakta hai. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Defence in depth

Kai independent, imperfect safety layers ek ke upar ek lagana. Jo attack ek layer se nikal jaaye, use dusri pakad le. → [13.1 Agents ke liye threat model](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Directed acyclic graph (DAG)

Tasks ka set jo one-way dependency arrows se jude hain, aur koi loop nahi hai. Aise plans ko ek valid order mein lagaya ja sakta hai, aur independent tasks parallel chal sakte hain. → [7.3 Task decomposition](docs/07-planning-and-reasoning/07.3-task-decomposition.md)

### Done criterion

Ek test jo batata hai ki task kab poora hua, jaise "the lunch total in EUR is known". Sabse achhe criteria woh hain jo code check kar sake. → [7.3 Task decomposition](docs/07-planning-and-reasoning/07.3-task-decomposition.md)

### Dual LLM pattern

Ek design jisme privileged model plan karta hai aur tools call karta hai, lekin untrusted text kabhi nahi padhta. Untrusted text ek quarantined model padhta hai jiske paas koi tool nahi. Code dono ke beech results sirf variable references ke roop mein pass karta hai. → [13.2 Prompt injection aur uske defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## E

### Embedding

Numbers ki list jo text ke matlab ko represent karti hai. Milte-julte matlab wale texts ke embeddings paas-paas hote hain. Isi se matlab ke basis par search ho paata hai. → [6.2 Embeddings aur vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### Environment variable

Ek named setting jo program ko code mein likhne ki jagah uske environment se milti hai, jaise `ANTHROPIC_API_KEY`. Model SDKs tumhari API key isi se padhte hain. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Episodic memory

Purane experiences ki long-term memory: agent ne kaun sa task kiya, kya try kiya aur result kya raha. Milte-julte purane runs se seekhne ke liye ise yaad kiya jaata hai. → [5.4 Episodic, semantic aur procedural memory](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md)

### Eval

Evaluation ka short form. Ek repeatable test jo naapta hai ki LLM system example tasks ke set par kitna achha perform karta hai. → [12.1 Agents ke evals mushkil kyun hain?](docs/12-evaluation/12.1-why-agent-evals-are-hard.md)

### Evaluator-optimizer

Ek loop jisme ek LLM call result banata hai aur alag evaluator use clear criteria par grade karke feedback deta hai. Generator tab tak sudhaarta hai jab tak result pass na ho ya round limit na aa jaye. → [8.2 Evaluator–optimizer loop](docs/08-reflection-and-self-correction/08.2-evaluator-optimizer-loop.md)

### Exponential backoff

Retry ka tarika jisme har failure ke baad wait double hota hai (jaise 0.5 s, 1 s, 2 s, 4 s), ek cap tak. Isse pareshaan service ko theek hone ka time milta hai. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Extended thinking

Reply se pehle model andar hi andar jo reasoning karta hai. Yeh alag thinking blocks mein aati hai (aksar hidden ya summarized) aur output tokens ki tarah bill hoti hai. Built-in reasoning ke liye yeh Anthropic ka naam hai. → [7.1 Chain-of-thought aur extended thinking](docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md)

## F

### Fake model

Asli LLM ki jagah ek stand-in jo scripted replies deta hai. Isse agent code offline, free aur deterministic tarike se test ho sakta hai. MockLLM aisa hi ek hai; zyada tar frameworks apna khud ka dete hain. → [11.1 Frameworks ka poora naksha](docs/11-frameworks/11.1-framework-landscape.md)

### Function calling

Model ki yeh ability ki woh plain text ki jagah (ya saath mein) structured request bhej sake ki tumhare describe kiye tools mein se koi chalaya jaye. Tumhara code tool chalata hai aur result wapas bhejta hai. Ise *tool calling* ya *tool use* bhi kehte hain. → [3.3 Function calling kaise kaam karta hai](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

## G

### Gate

Workflow ke do steps ke beech plain code mein ek check, jaise "is this valid JSON?" ya "is it under 80 words?". Fail hone par workflow ruk jaata hai ya woh step retry karta hai, kharab output aage nahi bhejta. → [9.1 Prompt chaining](docs/09-agent-design-patterns/09.1-prompt-chaining.md)

### Guardrail

Model call se pehle ya baad chalne wala check jo unsafe ya invalid input aur output ko block, fix ya flag karta hai. → [13.4 Input aur output guardrails](docs/13-safety-and-guardrails/13.4-input-and-output-guardrails.md)

## H

### Hallucination

Jab model koi galat ya banayi hui baat aise bolta hai jaise woh sach ho, jaise aisi delivery date jiska uske paas koi data nahi tha. Tools ya retrieval se model ko asli data dene par yeh kam hota hai. → [1.2 Chatbot, workflow aur agent mein farak](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)

### Handoff

Conversation ka control ek agent se dusre ko dena. Dusra agent phir apne instructions aur tools ke saath seedha user ko jawab deta hai. Aksar model ko yeh transfer_to_billing jaise tool ke roop mein diya jaata hai. → [10.3 Peer-to-peer aur handoffs](docs/10-multi-agent-systems/10.3-peer-to-peer-and-handoffs.md)

### Health check

Ek sasta endpoint, jaise GET /healthz, jise load balancer ya orchestrator call karta hai. Isse decide hota hai ki service instance zinda hai aur traffic lena chahiye ya nahi. → [15.6 FastAPI aur Docker se deploy karna](docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md)

### Human-in-the-loop (HITL)

Ek design jisme agent chune hue points par ruk jaata hai. Wahan insaan action ko approve, edit ya reject kar sakta hai, ya case khud sambhal sakta hai. Uske baad run aage badhta hai. → [9.6 Human-in-the-loop](docs/09-agent-design-patterns/09.6-human-in-the-loop.md)

### Hybrid search

Retrieval jo keyword search (jaise BM25) aur vector search dono milata hai. Isse exact terms aur paraphrases dono mil jaate hain. Dono result lists ko aksar reciprocal rank fusion se merge karte hain. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

## I

### Idempotency key

Side effect wali request ke saath bheji gayi unique id. Isse receiver same request ka retry pehchaan leta hai aur do baar kaam karne ki jagah pehla result lauta deta hai. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Idempotent

Aisa operation jiska effect same rehta hai chahe woh ek baar chale ya kai baar. Jaise thermostat ko 21°C par set karna. Idempotent operations ko retry karna safe hai. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Indirect prompt injection

Prompt injection jo user se nahi, balki us content se aata hai jo agent padhta hai, jaise web page, email, document ya tool result. → [13.2 Prompt injection aur uske defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

### Instructions

Agent ka woh hissa jo model ko uska role, goal, rules aur tools use karne ka tarika batata hai. Aksar yeh system prompt ke roop mein likha jaata hai. → [1.5 Agent ke andar kya-kya hota hai](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## J

### Jitter

Retry waits mein daali gayi randomness. Isse jo bahut saare clients ek hi pal mein fail hue, woh sab ek hi pal mein retry nahi karte. → [15.3 Queues, retries aur idempotency](docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md)

### Job queue

System ke us hisse ke beech ka buffer jo kaam leta hai, aur un workers ke beech jo kaam karte hain. Yeh achanak aaye load ko sambhal leta hai aur worker crash hone par bhi jobs safe rakhta hai. → [15.1 Production agent ka architecture](docs/15-production-and-deployment/15.1-production-architecture.md)

### JSON Schema

JSON data ki shape describe karne ka standard tarika: kaun se fields hain, unke types kya hain, kaun required hain aur kaun si values allowed hain. Tool definitions tool ke inputs describe karne ke liye ise use karti hain. → [3.2 Tool definitions ke liye JSON Schema](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md)

### JSON-RPC

JSON mein likha remote procedure calls ka simple message format. Har request mein id, method aur params hote hain. Har response mein wahi id hoti hai, saath mein result ya error. MCP messages JSON-RPC 2.0 use karte hain. → [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

## L

### Large language model (LLM)

Ek neural network jo bahut saare text par train hua hai taaki agla [token](#token) predict kar sake. Prompt milne par yeh ek-ek token karke text banata hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Least privilege

System ke har hisse ko, agent aur uske tools samet, sirf utna access dena jitna uske task ke liye chahiye, aur sirf utni der ke liye. → [13.3 Least-privilege tools aur sandboxing](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md)

### Lethal trifecta

Simon Willison ka diya naam us agent ke liye jisme teen cheezein ek saath hain: private data ka access, untrusted content se exposure, aur bahar communicate karne ka tarika. Teeno milkar attacker ko data churane dete hain. Koi ek leg hata do, to woh attack khatam. → [13.1 Agents ke liye threat model](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### LLM-as-judge

Language model se kisi dusre model ya agent ka output rubric ke against grade karwana, jo structured verdict deta hai. Bharosa karne se pehle ise human labels se check karna zaroori hai. → [12.3 LLM-as-judge: model se grading karwao](docs/12-evaluation/12.3-llm-as-judge.md)

### Long-term memory

Woh information jo agent runs ke beech sambhaal ke rakhta hai, jaise user preferences, purane results ya documents. Code ise store karta hai aur zaroorat par relevant hisse context mein wapas daalta hai. → [1.5 Agent ke andar kya-kya hota hai](docs/01-foundations/01.5-anatomy-of-an-agent.md)

## M

### Max tokens

Tumhari set ki hui limit ki model ek reply mein kitne tokens likh sakta hai. Limit aa gayi to reply beech mein kat jaata hai, aur stop reason yahi batata hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### MCP client

MCP host ke andar ka connector jo exactly ek MCP server se baat karta hai, aur use tools/list aur tools/call jaisi requests bhejta hai. → [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### MCP host

Woh AI application jo MCP servers use karti hai, jaise desktop chat app, IDE ya tumhara apna agent. Yeh har server ke liye ek MCP client chalata hai, model ke saath kaam karta hai aur user consent enforce karta hai. → [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### MCP prompt

MCP server ka diya hua reusable message template, jise user chunta hai, aksar slash command ke roop mein. Yeh teen server primitives mein se ek hai; baaki do tools aur resources hain. → [4.3 Tools, resources aur prompts](docs/04-model-context-protocol/04.3-tools-resources-and-prompts.md)

### MCP resource

MCP server ka diya hua read-only data jo URI se pehchaana jaata hai, jaise koi file ya database schema. Host application decide karti hai ki ise model ke context mein kab jodna hai. → [4.3 Tools, resources aur prompts](docs/04-model-context-protocol/04.3-tools-resources-and-prompts.md)

### MCP server

Ek program jo kisi ek system (jaise GitHub, database ya tumhare notes) ke tools, resources aur prompts ko Model Context Protocol ke through expose karta hai. Isse koi bhi MCP host unhe use kar sakta hai. → [4.4 Ek simple MCP server banao](docs/04-model-context-protocol/04.4-build-a-simple-mcp-server.md)

### Mean reciprocal rank (MRR)

Ek retrieval metric. Har query ke liye pehle relevant result ki position ka 1 divided by (koi na mile to 0), phir saari queries ka average. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

### MockLLM

Ek fake model jo pehle se likhe responses order mein lautata hai. Isse agent code aur tests offline, free aur har baar same result ke saath chalte hain. Tum ise das lines mein likh sakte ho. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

### Model cascade

Routing ka tarika jisme pehle sasta model try hota hai, uska answer check hota hai, aur check fail hone par hi request zyada capable model ko jaati hai. → [16.3 Model routing](docs/16-cost-and-performance/16.3-model-routing.md)

### Model Context Protocol (MCP)

Ek open protocol jo standard karta hai ki applications models ko tools, data aur prompts ka access kaise dein. Isse ek integration bahut saare apps mein chal jaata hai. → [4.1 MCP kyun bana?](docs/04-model-context-protocol/04.1-why-mcp-exists.md)

### Model fallback

Jab pehla model ya provider unavailable ho, overloaded ho ya request decline kar de, tab request ko dusre model ya provider par bhej dena. → [15.5 Rate limits aur fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Model gateway

Woh single component jisse har model call guzarti hai. Yeh retries, rate limits, models ya providers ke beech fallbacks sambhalta hai, aur tokens aur cost record karta hai. → [15.1 Production agent ka architecture](docs/15-production-and-deployment/15.1-production-architecture.md)

### Model routing

Har request ke liye chunna ki kaun sa model use sambhalega. Jaise aasan kaam chhote, saste model ko aur mushkil kaam bade model ko. Iske liye rules, classifier ya cascade use hota hai. → [16.3 Model routing](docs/16-cost-and-performance/16.3-model-routing.md)

### Multi-agent system

Aisa system jisme kai agents, har ek apne instructions, tools aur context ke saath, ek task par kaam karte hain. Woh ek dusre ko kaam delegate karte hain ya hand over karte hain. → [10.1 Multiple agents kyun?](docs/10-multi-agent-systems/10.1-why-multiple-agents.md)

### Multi-hop question

Aisa sawal jisme do ya zyada lookups chahiye, aur baad wali search pehli search ke result par depend karti hai. Jaise "the price of the plan that includes SSO". → [6.4 Agentic RAG](docs/06-rag-for-agents/06.4-agentic-rag.md)

## N

### nDCG

Normalised discounted cumulative gain. Ek retrieval metric jo sabse relevant results ko upar rakhne par reward deta hai. Isme graded relevance hoti hai aur neeche ki positions ke liye discount. 1.0 ka matlab ideal order. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

## O

### Observability

Chalte hue system ke baare mein "kya hua, aur kyun?" ka jawab uske record kiye data (traces, logs aur metrics) se de paana, bina pehle naya code jode. → [14.1 Agent runs ko trace karna](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### Observation

Action ke baad agent ko jo result dikhta hai, jaise tool ka output ya error. Ise conversation mein joda jaata hai taaki model agle decision mein use kar sake. ReAct mein yeh woh line hai jo tumhara code har Action ke baad likhta hai. → [2.1 Observe–think–act loop](docs/02-the-agent-loop/02.1-the-observe-think-act-loop.md)

### OpenTelemetry (OTel)

Traces, metrics aur logs banane aur export karne ka open, vendor-neutral standard aur libraries ka set. Isse same instrumentation bahut saare backends ke saath chal jaata hai. → [14.3 LLM apps ke liye OpenTelemetry](docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md)

### Orchestrator-workers

Ek pattern jisme lead LLM call task ko run time par decide hue sub-tasks mein todti hai. Har worker call ek sub-task sambhalti hai, aur lead unke results jodti hai. → [9.4 Orchestrator–workers](docs/09-agent-design-patterns/09.4-orchestrator-workers.md)

## P

### Parallel tool calls

Ek hi turn mein model ki taraf se aaye kai tool calls. Tumhara code unhe ek saath chala sakta hai, lekin har call ka ek result lautana zaroori hai, ID se match karke. → [3.5 Parallel tool calls](docs/03-tools-and-function-calling/03.5-parallel-tool-calls.md)

### Parallelisation

Independent LLM calls ek saath chalana aur code mein results jodna. Ya to alag-alag subtasks (sectioning), ya same task kai baar chala kar vote se faisla (voting). → [9.3 Parallelisation (sectioning aur voting)](docs/09-agent-design-patterns/09.3-parallelisation.md)

### pass@k (pass at k)

Chance ki k independent attempts mein se kam se kam ek successful ho. k badhne par yeh 1 ki taraf badhta hai. Yeh un tasks ke liye theek hai jahan tum automatically kaam karne wala attempt chun sakte ho. → [12.2 Task, trajectory aur tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### pass^k (pass hat k)

Chance ki saare k independent attempts successful hon. k badhne par yeh girta hai. Yeh woh consistency naapta hai jo customer-facing agents ko chahiye. → [12.2 Task, trajectory aur tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Personally identifiable information (PII)

Woh information jisse kisi insaan ki pehchaan ho sake, jaise naam, email address, phone number, card number ya ID number. → [13.6 Secrets aur PII handling](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md)

### Plan-and-execute

Agent pattern jisme planner pehle poora plan likhta hai aur executor use ek-ek step karke poora karta hai. Code plan ko validate aur schedule karta hai. → [7.2 Plan-and-execute](docs/07-planning-and-reasoning/07.2-plan-and-execute.md)

### Position bias

Judge model ki aadat ki woh answer ko uski jagah ki wajah se pasand kare (jaise pehle aaya hai), na ki uske content ki wajah se. Iska ilaaj: order badal kar do baar poochho. → [12.3 LLM-as-judge: model se grading karwao](docs/12-evaluation/12.3-llm-as-judge.md)

### Precision and recall at k

Do retrieval metrics. Precision@k: top k results mein se kitna hissa relevant hai. Recall@k: saare relevant documents mein se kitna hissa top k mein aaya. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

### Procedural memory

Kaam kaise karna hai, uski long-term memory: instructions, rules aur code, plus jo model ne training mein seekha. Feedback se seekhe rules dhyan se jode ja sakte hain. → [5.4 Episodic, semantic aur procedural memory](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md)

### Prompt caching

Provider ka feature jo request ki unchanged shuruaat (prefix) par pehle se kiya kaam reuse karta hai. Isse baar-baar aane wale input tokens bahut saste aur jaldi process hote hain. → [16.2 Prompt caching](docs/16-cost-and-performance/16.2-prompt-caching.md)

### Prompt chaining

Workflow jo task ko LLM calls ke fixed sequence mein todta hai. Har call pichhli call ke output par kaam karti hai, aur aksar steps ke beech code mein gates hote hain. → [9.1 Prompt chaining](docs/09-agent-design-patterns/09.1-prompt-chaining.md)

### Prompt injection

Ek attack jisme model jo text padhta hai (jaise user message, web page ya tool result), usme aise instructions hote hain jo developer ke instructions ko override karne ke liye banaye gaye hain. → [13.2 Prompt injection aur uske defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

## Q

### Query rewriting

User ke sawal ko behtar search queries mein badalna. Jaise product names jodna, synonyms use karna, ya har fact ke liye alag query banana. → [6.4 Agentic RAG](docs/06-rag-for-agents/06.4-agentic-rag.md)

## R

### Rate limit

Provider ki lagayi cap ki ek time window mein tum kitna bhej sakte ho, jaise requests ya tokens per minute. Isse upar gaye to HTTP 429 milta hai. → [15.5 Rate limits aur fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Re-planning

Koi step fail hone ke baad bache hue kaam ke liye naya plan likhna. Poore ho chuke steps rakhe jaate hain aur failure ki wajah use hoti hai. Yeh attempts ki fixed limit ke andar hota hai. → [7.5 Jab kuch fail ho, tab re-planning](docs/07-planning-and-reasoning/07.5-re-planning-when-things-fail.md)

### Re-ranker

Ek model jo retrieved passages ki chhoti list ko dobara score karta hai, query aur har passage ko saath padh kar (aksar cross-encoder). First-stage search se slow hai, lekin zyada accurate. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

### ReAct

"Reasoning and Acting" ka short form. Ek pattern jisme model baari-baari reasoning step likhta hai aur action leta hai, phir aage badhne se pehle observation padhta hai. Yao et al. (2022) ne introduce kiya. → [2.2 ReAct ko samjho](docs/02-the-agent-loop/02.2-react-explained.md)

### Reasoning effort

Request ki setting jo control karti hai ki model jawab se pehle kitna soche, jaise low, medium ya high. Claude ise output_config.effort ke roop mein leta hai; OpenAI reasoning.effort ya reasoning_effort ke roop mein. → [7.1 Chain-of-thought aur extended thinking](docs/07-planning-and-reasoning/07.1-chain-of-thought-and-extended-thinking.md)

### Reciprocal rank fusion (RRF)

Kai ranked lists ko sirf positions se merge karne ka tarika. Har document ka score un lists par 1 / (k + rank) ka sum hota hai jinme woh aata hai. → [6.5 Re-ranking aur retrieval evaluation](docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md)

### Redaction

Text ke sensitive values ko placeholders ya masks se badalna, jaise email address ko <EMAIL_1> bana dena. Yeh text ke model ya log tak pahunchne se pehle hota hai. → [13.6 Secrets aur PII handling](docs/13-safety-and-guardrails/13.6-secrets-and-pii.md)

### Reflection

Ek pattern jisme model draft answer likhta hai, phir draft ki kamiyan nikalta hai (aksar alag critic prompt aur checklist se), aur use sudhaarta hai. Yeh tab tak repeat hota hai jab tak critique ko koi problem na mile ya round limit na aa jaye. → [8.1 Reflection pattern](docs/08-reflection-and-self-correction/08.1-the-reflection-pattern.md)

### Regression test

Ek test jo fix kiye gaye bug ko pakad ke rakhta hai, jaise record kiya hua failing agent run. Bug kabhi wapas aaya to automatically pakda jayega. → [14.5 Bigde hue agent ko debug karna](docs/14-observability-and-debugging/14.5-debugging-a-broken-agent.md)

### Retrieval-augmented generation (RAG)

Ek technique jo pehle relevant documents retrieve karti hai, phir unhe sawal ke saath model ko deti hai. Isse answer us information par based rehta hai. → [6.1 RAG, 5 minute mein](docs/06-rag-for-agents/06.1-rag-in-5-minutes.md)

### Routing

Workflow jo pehle input ko classify karta hai, label check karta hai, phir input ko us kism ke input ke liye specialised handler (prompt, tools ya model) ko bhejta hai. → [9.2 Routing](docs/09-agent-design-patterns/09.2-routing.md)

### Rubric

Criteria ki likhi hui list, har ek ka clear pass/fail rule. Human ya model grader ise use karta hai taaki grading consistent rahe. → [12.3 LLM-as-judge: model se grading karwao](docs/12-evaluation/12.3-llm-as-judge.md)

### Rug pull

Jab MCP server user ke approve karne ke baad apne tool definitions ya behaviour badal deta hai, jaise description mein hidden instructions jod dena. Tool definitions ko pin karna isse bachata hai. → [4.6 MCP servers ki security](docs/04-model-context-protocol/04.6-mcp-security.md)

### Run budget

Limits ki ek agent run kitne steps, tokens, dollars aur seconds use kar sakta hai. Har model call se pehle loop mein check hoti hain, taaki limit aate hi run araam se ruk jaye. → [16.5 Har run ki budget limits](docs/16-cost-and-performance/16.5-budget-limits-per-run.md)

## S

### Sampling

Model apni predicted probabilities se har agla token kaise chunta hai, hamesha sabse likely wala lene ki jagah. Isi wajah se same prompt alag-alag replies de sakta hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Sandbox

Ek isolated, use-and-throw environment, jaise locked-down container ya microVM. Wahan agent ka code limited files, network aur resources ke saath chalta hai, aur koi secrets nahi hote. → [13.3 Least-privilege tools aur sandboxing](docs/13-safety-and-guardrails/13.3-least-privilege-and-sandboxing.md)

### Self-correction

Model ka apna output khud sudhaarna. Intrinsic self-correction sirf wahi use karta hai jo model pehle se jaanta hai, aur reasoning ke liye bharosemand nahi hai. External feedback (tests, errors, tool results) ke saath self-correction kahin behtar kaam karta hai. → [8.4 Self-correction ki limits](docs/08-reflection-and-self-correction/08.4-limits-of-self-correction.md)

### Semantic conventions

OpenTelemetry mein span names aur attributes ke liye tay kiye gaye naam aur matlab, jaise gen_ai.usage.input_tokens. Isse har backend kisi bhi instrumented app ka data padh sakta hai. → [14.3 LLM apps ke liye OpenTelemetry](docs/14-observability-and-debugging/14.3-opentelemetry-for-llm-apps.md)

### Semantic memory

User, duniya ya khud agent ke baare mein facts ki long-term memory, jaise "the user is vegetarian". Same fact ki nayi value purani ko replace kare. → [5.4 Episodic, semantic aur procedural memory](docs/05-memory/05.4-episodic-semantic-and-procedural-memory.md)

### Server tool

Aisa tool jise model provider API call ke andar apne infrastructure par chalata hai, jaise web search ya code execution. Tumhara code ise execute nahi karta. → [3.6 Code execution ek tool ki tarah](docs/03-tools-and-function-calling/03.6-code-execution-as-a-tool.md)

### Server-sent events (SSE)

Ek simple HTTP standard jisse server ek lambe chalne wale response par client ko events ki stream bhejta hai. Aksar agent ki progress browser tak stream karne ke liye use hota hai. → [15.2 Sync vs async aur background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Short-term memory

Current run ke dauraan agent jo jaanta hai: ab tak ki conversation, har tool call aur result samet. Yeh context window mein rehti hai. → [1.5 Agent ke andar kya-kya hota hai](docs/01-foundations/01.5-anatomy-of-an-agent.md)

### Span

Trace ke andar ek timed step, jaise model call ya tool call. Isme naam, start aur end time, attributes, status aur parent step ka link hota hai. → [14.1 Agent runs ko trace karna](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### State graph

Agent ko nodes (steps) aur edges (aage kya chalega) se banane ka tarika. Saare nodes ek shared state object padhte aur update karte hain. Yeh LangGraph ka core abstraction hai. → [11.2 LangGraph](docs/11-frameworks/11.2-langgraph.md)

### Stateless

Aisi API jo calls ke beech kuch yaad nahi rakhti. LLM APIs stateless hain, isliye tumhare code ko har baar poori conversation dobara bhejni padti hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### stdio transport

MCP transport jisme host server ko local subprocess ki tarah start karta hai. Dono uske standard input aur output par newline-delimited JSON-RPC messages ka lena-dena karte hain. → [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### Stop reason

Model ke reply ka woh field jo batata hai ki usne likhna kyun roka: kaam khatam hua, tool call karna chahta hai, output limit aa gayi, ya usne mana kar diya. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Stopping condition

Agent run khatam karne ka rule. Achha wala hai poora final answer. Safety wale woh limits hain jo tumhara code enforce karta hai, jaise maximum steps, time, tokens, cost ya baar-baar same calls. → [2.4 Agent kab ruke: stopping conditions](docs/02-the-agent-loop/02.4-stopping-conditions.md)

### Streamable HTTP

Un servers ke liye MCP transport jo alag se chalte hain, aksar remote. Client har message ek endpoint par HTTP POST karke bhejta hai, aur reply JSON ya us request ke events ki stream ke roop mein aata hai. → [4.2 Hosts, clients aur servers](docs/04-model-context-protocol/04.2-hosts-clients-and-servers.md)

### Streaming

Model ka reply bante-bante tukdon mein lena, end mein ek saath nahi. Isse users ko pehle words jaldi dikhte hain. → [16.4 Latency kam karna](docs/16-cost-and-performance/16.4-latency-optimisation.md)

### Strict mode

Tool option (`strict: true`) jisse provider model ka output constrain karta hai, taaki tool arguments hamesha JSON Schema se match karein. Anthropic aur OpenAI dono yeh dete hain, thode alag schema rules ke saath. → [3.2 Tool definitions ke liye JSON Schema](docs/03-tools-and-function-calling/03.2-json-schema-for-tools.md)

### Structured logging

Har log entry ko free-text sentence ki jagah data ki tarah likhna (aksar named fields wala ek JSON object). Isse logs search, filter aur count ho sakte hain. → [14.2 Tool calls ko log karna](docs/14-observability-and-debugging/14.2-logging-tool-calls.md)

### Subagent

Ek agent jise dusra agent apne context mein ek focused sub-task karne ke liye start karta hai. Use ek brief milta hai aur woh sirf apna final result lautata hai. → [10.2 Supervisor aur hierarchical](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md)

### Supervisor agent

Ek agent jo task ka control apne paas rakhta hai, uske hisse specialist agents ko delegate karta hai (jo aksar use tools ki tarah diye jaate hain) aur unke results jodta hai. Ise lead, orchestrator ya manager agent bhi kehte hain. → [10.2 Supervisor aur hierarchical](docs/10-multi-agent-systems/10.2-supervisor-and-hierarchical.md)

### Sycophancy

Model ki aadat ki woh user se ya prompt ke ishaare se sehmat ho jaye, chahe iske liye sahi answer chhodna pade. Isi wajah se "are you sure?" poochh kar answer check karna achha tarika nahi hai. → [8.4 Self-correction ki limits](docs/08-reflection-and-self-correction/08.4-limits-of-self-correction.md)

### System prompt

User ke messages se alag model ko diye gaye instructions. Inse poori conversation ke liye model ka role, rules aur behaviour set hota hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

## T

### Taint tracking

Yaad rakhna ki untrusted content kab agent ke context mein aaya, aur us point se risky actions (jaise data bahar bhejna) par rok lagana. → [13.2 Prompt injection aur uske defences](docs/13-safety-and-guardrails/13.2-prompt-injection.md)

### Task decomposition

Goal ko chhote sub-tasks mein todna. Har sub-task ka ek outcome, ek done criterion aur dusre sub-tasks par clear dependencies hoti hain. → [7.3 Task decomposition](docs/07-planning-and-reasoning/07.3-task-decomposition.md)

### Temperature

Sampling setting jo control karti hai ki model ka output kitna random ho: kam matlab zyada predictable, zyada matlab zyada variety. Kai recent models ab ise accept nahi karte, aur 0 par bhi outputs badal sakte hain. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Text-to-SQL

Simple bhasha ke sawal ko aisi SQL query mein badalna jo uska jawab de. Aksar query ke results ko reference query ke results se compare karke evaluate kiya jaata hai. → [17.4 Data analysis agent](docs/17-case-studies/17.4-data-analysis-agent.md)

### Threat model

System ke baare mein chaar sawalon ka likha hua jawab: kya keemti hai, kaun attack kar sakta hai, woh andar kaise aa sakte hain, aur kya nuksaan kar sakte hain. → [13.1 Agents ke liye threat model](docs/13-safety-and-guardrails/13.1-threat-model-for-agents.md)

### Time to first token (TTFT)

Request bhejne ke kitni der baad response ka pehla token aata hai. Model ko jitna zyada uncached input padhna ho, yeh utna badhta hai. → [16.4 Latency kam karna](docs/16-cost-and-performance/16.4-latency-optimisation.md)

### Token

Text ki woh unit jo model padhta aur likhta hai: aksar ek word, word ka hissa, ya punctuation mark. Context windows, limits aur prices sab tokens mein naape jaate hain. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Token bucket

Rate-limiting algorithm. Tokens ek steady rate se maximum tak refill hote hain, har request ek token leti hai, aur bucket khaali ho to requests wait karti hain. Yeh chhote bursts allow karta hai lekin average rate par cap rakhta hai. → [15.5 Rate limits aur fallbacks](docs/15-production-and-deployment/15.5-rate-limits-and-fallbacks.md)

### Token passthrough

Ek anti-pattern jisme MCP server aisa access token accept kar leta hai jo uske liye issue hi nahi hua tha, aur use kisi dusri API ko forward kar deta hai. MCP authorization specification ise mana karti hai. → [4.6 MCP servers ki security](docs/04-model-context-protocol/04.6-mcp-security.md)

### Tokenizer

Woh component jo model ke padhne se pehle text ko tokens mein todta hai. Har provider ka apna hota hai, isliye same text alag models par alag token count deta hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Tool

Ek function jo tumhara code model ko expose karta hai, naam, description aur input schema ke saath. Model use chalane ko keh sakta hai; tumhara code use chalata hai aur result lautata hai. → [3.1 Tool kya hota hai?](docs/03-tools-and-function-calling/03.1-what-is-a-tool.md)

### Tool call

Ek tool chalane ki model ki structured request: tool ka naam, uske arguments aur ek ID. Tumhara code use chalata hai aur same ID wale tool result se reply karta hai. → [3.3 Function calling kaise kaam karta hai](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Tool choice

Request ki setting jo control karti hai ki is turn par model tool call kar sakta hai, use karna hi padega, koi specific tool call karna padega, ya koi bhi tool call nahi kar sakta. → [3.3 Function calling kaise kaam karta hai](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Tool poisoning

Ek attack jo model ke liye instructions tool ke naam, description ya schema mein chhupa deta hai. Isse sirf tool connect karne se hi agent bhatak sakta hai, jaise files leak karna. → [4.6 MCP servers ki security](docs/04-model-context-protocol/04.6-mcp-security.md)

### Tool result

Tool call chalane ke baad tumhara code jo message wapas bhejta hai, ID se us call se juda hua. Isme tool ka output hota hai, ya aisa error message jise model padh kar kuch kar sake. → [3.3 Function calling kaise kaam karta hai](docs/03-tools-and-function-calling/03.3-how-function-calling-works.md)

### Trace

Ek request ya agent run ka record, spans ke tree ki tarah jinki trace ID same hai. Root par run hota hai, aur model calls aur tool calls uske children. → [14.1 Agent runs ko trace karna](docs/14-observability-and-debugging/14.1-tracing-agent-runs.md)

### Trajectory

Ek run mein agent ke liye gaye steps ki ordered list, khaas kar tool calls aur unke arguments. Evals ise expected trajectory se compare karte hain taaki sirf result nahi, raasta bhi check ho. → [12.2 Task, trajectory aur tool-use metrics](docs/12-evaluation/12.2-task-trajectory-and-tool-metrics.md)

### Transformer

Modern LLMs ke peeche ka neural network architecture, 2017 mein introduce hua. Isme agla token predict karte waqt har token pichhle saare tokens ko dhyan mein le sakta hai. → [1.4 LLMs kaise kaam karte hain (bas utna jitna zaroori hai)](docs/01-foundations/01.4-how-llms-work.md)

### Tree of thoughts (ToT)

Search ka tarika jisme model kai possible next steps propose karta hai, unhe evaluate karta hai, sabse promising wale rakhta hai aur aage badhta hai. Aise woh partial solutions ka tree explore karta hai. Yao et al. (2023) ne introduce kiya. → [7.4 Tree-of-thoughts (ek overview)](docs/07-planning-and-reasoning/07.4-tree-of-thoughts.md)

## V

### Vector database

Embeddings ka store, unke text aur metadata ke saath. Yeh query vector ke sabse kareeb wale vectors jaldi lauta sakta hai, aksar approximate nearest neighbour index se. → [6.2 Embeddings aur vector databases](docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)

### Vector memory

Text plus embeddings ke roop mein store ki gayi long-term memory. Yaad karte waqt woh memories nikaali jaati hain jinke embeddings query se sabse zyada milte hain. → [5.3 Vector memory](docs/05-memory/05.3-vector-memory.md)

### Virtual environment

Ek project ke Python packages ka apna alag folder, taaki uski dependencies dusre projects se na takrayein. `python -m venv .venv` se banta hai. → [0.3 Setup](docs/00-start-here/00.3-setup.md)

## W

### Webhook

Ek HTTP request jo system kuch hone par (jaise agent run khatam hone par) tumhare registered URL par bhejta hai. Isse tumhe baar-baar poll nahi karna padta. → [15.2 Sync vs async aur background agents](docs/15-production-and-deployment/15.2-sync-vs-async-agents.md)

### Workflow

Ek LLM system jisme steps ka sequence tumhara code pehle se fix karta hai, aur model kuch hisse bharta hai, jaise text likhna ya input classify karna. Agent se farak: wahan steps model chunta hai. → [1.2 Chatbot, workflow aur agent mein farak](docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md)
