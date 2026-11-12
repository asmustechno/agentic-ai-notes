"""The A2A subset: Agent Card discovery, tasks, multi-turn input, artifacts. Offline, with MockLLM."""

from fastapi.testclient import TestClient

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def make(script: list[str]) -> tuple:
    llm = MockLLM(script)
    http = TestClient(main.create_server(llm), base_url=main.BASE_URL)
    return main.A2AClient(http), http, llm


def test_agent_card_is_served_at_the_well_known_path() -> None:
    _, http, _ = make([])
    card = http.get("/.well-known/agent-card.json").json()
    assert card["name"] == "Currency Agent"
    assert card["skills"][0]["id"] == "convert"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "HTTP+JSON"


def test_client_uses_the_endpoint_from_the_card() -> None:
    client, _, _ = make([])
    client.discover()
    assert client.endpoint == "/a2a"


def test_complete_request_returns_completed_task_with_artifact() -> None:
    client, _, _ = make(['{"amount": 100, "from": "USD", "to": "EUR"}'])
    client.discover()
    task = client.send("100 USD in EUR?")
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    parts = task["artifacts"][0]["parts"]
    assert parts[0]["text"] == "100 USD = 92.0 EUR"
    assert parts[1]["data"]["converted"] == 92.0


def test_multi_turn_task_keeps_its_id_and_history() -> None:
    client, http, llm = make(main.REMOTE_SCRIPT)
    client.discover()
    first = client.send("Please convert 250 GBP.")
    assert first["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert first["status"]["message"]["role"] == "ROLE_AGENT"
    second = client.send("To EUR.", task_id=first["id"])
    assert second["id"] == first["id"] and second["status"]["state"] == "TASK_STATE_COMPLETED"
    # the remote agent saw both turns of the task
    assert llm.calls[1]["messages"][0]["content"] == "Please convert 250 GBP. To EUR."
    full = http.get(f"/a2a/tasks/{first['id']}", headers={"A2A-Version": "1.0"}).json()
    assert [m["role"] for m in full["history"]] == ["ROLE_USER", "ROLE_USER"]


def test_unsupported_pair_fails_the_task() -> None:
    client, _, _ = make(['{"amount": 5, "from": "JPY", "to": "CHF"}'])
    client.discover()
    assert client.send("5 JPY to CHF")["status"]["state"] == "TASK_STATE_FAILED"


def test_missing_version_header_is_rejected() -> None:
    _, http, _ = make([])
    resp = http.post("/a2a/message:send", json={"message": {"role": "ROLE_USER", "parts": [{"text": "hi"}]}})
    assert resp.status_code == 400


def test_caller_never_sees_the_remote_prompt() -> None:
    client, _, llm = make(['{"amount": 1, "from": "GBP", "to": "EUR"}'])
    client.discover()
    task = client.send("1 GBP to EUR")
    assert main.REMOTE_PROMPT not in str(task) and main.REMOTE_PROMPT not in str(client.card)
    assert llm.calls[0]["system"] == main.REMOTE_PROMPT  # it exists, but stays on the server (opaque agent)
