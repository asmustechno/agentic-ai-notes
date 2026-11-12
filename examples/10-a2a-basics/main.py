"""A2A in miniature: discover a remote agent from its Agent Card, send it a message, follow the task.

    client agent ──GET /.well-known/agent-card.json──▶ remote "currency agent" (FastAPI)
                 ──POST /message:send ───────────────▶ returns a Task (state + artifacts)
                 ──POST /message:send (taskId=...) ──▶ continues a task that needs input

This is a *teaching subset* of the A2A v1.0 HTTP+JSON binding (Agent Card,
SendMessage, GetTask, task states, parts and artifacts), small enough to read
in one go. It is not a complete or compliant implementation: for real
systems use an official SDK (for Python, `pip install a2a-sdk`).

Everything runs in one process: FastAPI's TestClient calls the server
without opening a network port, so the demo and its tests work offline.

    python main.py                 # from this folder
    python 10-a2a-basics/main.py   # from examples/

Read alongside docs/10-multi-agent-systems/10.5-agent-to-agent-protocols.md.
"""

from __future__ import annotations

import itertools
import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from common import LLM, MockLLM, get_llm, user  # noqa: E402

BASE_URL = "https://currency-agent.example.com"
A2A_VERSION = "1.0"

# --------------------------------------------------------------------------- the remote agent (server side)

AGENT_CARD: dict[str, Any] = {
    "name": "Currency Agent",
    "description": "Converts amounts between currencies using today's reference rates.",
    "supportedInterfaces": [{"url": f"{BASE_URL}/a2a", "protocolBinding": "HTTP+JSON", "protocolVersion": A2A_VERSION}],
    "provider": {"organization": "Example Finance Ltd", "url": "https://finance.example.com"},
    "version": "0.1.0",
    "capabilities": {"streaming": False, "pushNotifications": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain", "application/json"],
    "skills": [
        {
            "id": "convert",
            "name": "Convert currency",
            "description": "Convert an amount from one currency to another.",
            "tags": ["finance", "currency"],
            "examples": ["How much is 250 GBP in EUR?"],
        }
    ],
}

RATES = {("GBP", "EUR"): 1.17, ("EUR", "GBP"): 0.855, ("USD", "EUR"): 0.92}

# The remote agent's own model decides whether it has enough information.
# It is opaque to the caller: the caller never sees this prompt or its tools.
REMOTE_PROMPT = (
    'Extract a conversion request. Reply with JSON only: {"amount": number, "from": "ISO code", "to": "ISO code"}, '
    'or {"missing": "what you still need"} if the request is incomplete.'
)


def create_server(llm: LLM) -> FastAPI:
    app = FastAPI()
    tasks: dict[str, dict[str, Any]] = {}
    ids = itertools.count(1)  # readable ids for the demo; real servers use UUIDs

    def check_version(request: Request) -> None:
        if request.headers.get("A2A-Version", "0.3") != A2A_VERSION:
            raise HTTPException(400, "Protocol version not supported")

    @app.get("/.well-known/agent-card.json")
    def agent_card() -> dict[str, Any]:
        return AGENT_CARD

    @app.post("/a2a/message:send")
    async def send_message(request: Request) -> dict[str, Any]:
        check_version(request)
        msg = (await request.json())["message"]
        text = " ".join(p["text"] for p in msg["parts"] if "text" in p)
        task = tasks.get(msg.get("taskId", "")) or {
            "id": f"task-{next(ids)}",
            "contextId": msg.get("contextId") or str(uuid.uuid4()),
            "history": [],
            "artifacts": [],
        }
        task["history"].append(msg)
        conversation = " ".join(" ".join(p["text"] for p in m["parts"] if "text" in p) for m in task["history"])
        try:
            reply = json.loads(llm.chat([user(conversation)], system=REMOTE_PROMPT, max_tokens=200).text)
        except json.JSONDecodeError:
            reply = {"missing": "the amount and both currencies, for example '250 GBP to EUR'"}

        if "missing" in reply:  # a multi-turn task: ask the caller for more
            question = {"role": "ROLE_AGENT", "messageId": str(uuid.uuid4()), "parts": [{"text": f"Please tell me {reply['missing']}."}]}
            task["status"] = {"state": "TASK_STATE_INPUT_REQUIRED", "message": question}
        else:
            rate = RATES.get((reply["from"], reply["to"]))
            if rate is None:
                task["status"] = {"state": "TASK_STATE_FAILED"}
            else:
                result = {"amount": reply["amount"], "from": reply["from"], "to": reply["to"], "rate": rate,
                          "converted": round(reply["amount"] * rate, 2)}
                task["artifacts"] = [{"artifactId": str(uuid.uuid4()), "name": "conversion",
                                      "parts": [{"text": f"{result['amount']} {result['from']} = {result['converted']} {result['to']}"},
                                                {"data": result}]}]
                task["status"] = {"state": "TASK_STATE_COMPLETED"}
        tasks[task["id"]] = task
        return {"task": {k: v for k, v in task.items() if k != "history"}}

    @app.get("/a2a/tasks/{task_id}")
    def get_task(task_id: str, request: Request) -> dict[str, Any]:
        check_version(request)
        if task_id not in tasks:
            raise HTTPException(404, "Task not found")
        return tasks[task_id]

    return app


# --------------------------------------------------------------------------- the calling agent's side (client)


class A2AClient:
    """Discover an agent, pick an interface it supports, and send messages."""

    def __init__(self, http: TestClient) -> None:
        self.http = http
        self.card: dict[str, Any] = {}
        self.endpoint = ""

    def discover(self) -> dict[str, Any]:
        self.card = self.http.get("/.well-known/agent-card.json").json()
        # Pick the first interface we support (the card lists them in the server's order of preference).
        iface = next(i for i in self.card["supportedInterfaces"] if i["protocolBinding"] == "HTTP+JSON")
        self.endpoint = iface["url"].removeprefix(BASE_URL)
        return self.card

    def send(self, text: str, task_id: str | None = None) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "ROLE_USER", "messageId": str(uuid.uuid4()), "parts": [{"text": text}]}
        if task_id:
            message["taskId"] = task_id  # continue an existing task
        resp = self.http.post(f"{self.endpoint}/message:send", json={"message": message},
                              headers={"A2A-Version": A2A_VERSION, "Content-Type": "application/a2a+json"})
        resp.raise_for_status()
        return resp.json()["task"]


REMOTE_SCRIPT = [
    '{"missing": "the currency you want to convert to"}',
    '{"amount": 250, "from": "GBP", "to": "EUR"}',
]


def main() -> None:
    server = create_server(get_llm(mock_responses=REMOTE_SCRIPT))
    client = A2AClient(TestClient(server, base_url=BASE_URL))

    card = client.discover()
    print(f"Discovered: {card['name']} v{card['version']} - skills: {[s['id'] for s in card['skills']]}")
    print(f"Endpoint:   {client.endpoint} ({card['supportedInterfaces'][0]['protocolBinding']}, A2A {A2A_VERSION})\n")

    task = client.send("Please convert 250 GBP.")
    print(f"-> SendMessage 'Please convert 250 GBP.'\n<- task {task['id']} state={task['status']['state']}")
    if task["status"]["state"] == "TASK_STATE_INPUT_REQUIRED":
        print(f"   agent asks: {task['status']['message']['parts'][0]['text']}")
        task = client.send("To EUR.", task_id=task["id"])
        print(f"-> SendMessage 'To EUR.' (taskId={task['id']})\n<- state={task['status']['state']}")
    for artifact in task["artifacts"]:
        print(f"   artifact '{artifact['name']}': {artifact['parts'][0]['text']}  data={artifact['parts'][1]['data']}")


if __name__ == "__main__":
    main()
