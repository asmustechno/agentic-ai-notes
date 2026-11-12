# 10 · A2A basics

A calling agent discovers a remote "currency agent" from its **Agent Card**, sends it a message, gets back a **task** that needs more input, answers, and receives the result as an **artifact**. Used in [10.5 Agent-to-agent protocols](../../docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md).

This is a teaching subset of the [A2A v1.0](https://a2a-protocol.org/latest/specification/) HTTP+JSON binding: the Agent Card at `/.well-known/agent-card.json`, `POST /message:send`, `GET /tasks/{id}`, the `A2A-Version` header, task states, parts and artifacts. It leaves out streaming, push notifications, authentication, signatures and most error handling. For real systems, use an official SDK (for Python, `pip install a2a-sdk`).

What to notice:

- **Discovery.** The client reads the card to learn the agent's skills and which endpoint and binding to use. Nothing is hard-coded except the domain.
- **Opaque agents.** The remote agent's prompt, model and rates stay on the server. The caller sees only the card, the task and the artifacts.
- **Tasks are stateful.** The first reply is `TASK_STATE_INPUT_REQUIRED`. The follow-up message carries the same `taskId`, and the server keeps the history.
- **Artifacts have parts.** The result comes as a `text` part for people and a `data` part (structured JSON) for programs.

Everything runs in one process through FastAPI's `TestClient`, so no network port is opened.

## Run it

```bash
cd examples
python 10-a2a-basics/main.py
```

Output (offline, with `MockLLM` as the remote agent's model):

```text
Discovered: Currency Agent v0.1.0 - skills: ['convert']
Endpoint:   /a2a (HTTP+JSON, A2A 1.0)

-> SendMessage 'Please convert 250 GBP.'
<- task task-1 state=TASK_STATE_INPUT_REQUIRED
   agent asks: Please tell me the currency you want to convert to.
-> SendMessage 'To EUR.' (taskId=task-1)
<- state=TASK_STATE_COMPLETED
   artifact 'conversion': 250 GBP = 292.5 EUR  data={'amount': 250, 'from': 'GBP', 'to': 'EUR', 'rate': 1.17, 'converted': 292.5}
```

## Test it

```bash
pytest 10-a2a-basics
```

## Things to try

- Add a second skill to the Agent Card (for example `list_currencies`) and make the client pick a skill by tag.
- Add `GET /tasks` (ListTasks) filtered by `contextId`.
- Replace the hand-written server with the official `a2a-sdk` and check that this client still works against it.
