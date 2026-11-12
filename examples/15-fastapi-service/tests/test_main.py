"""The agent service, tested in-process with FastAPI's TestClient and MockLLM. No server, no network, no key."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("httpx")  # TestClient needs it
from fastapi.testclient import TestClient  # noqa: E402

from common import LLM, MockLLM  # noqa: E402
from common.testing import load_example  # noqa: E402

main = load_example(__file__)


def make_client(settings: main.Settings | None = None, llms: list[MockLLM] | None = None) -> TestClient:
    """A TestClient whose runs use MockLLMs we can inspect afterwards."""
    created = llms if llms is not None else []

    def factory() -> LLM:
        llm = MockLLM([main.support_mock] * 6)
        created.append(llm)
        return llm

    return TestClient(main.create_app(settings or main.Settings(log_level="WARNING"), llm_factory=factory))


def test_health_check() -> None:
    with make_client() as client:
        r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


def test_sync_run_returns_the_answer_and_uses_the_tool() -> None:
    llms: list[MockLLM] = []
    with make_client(llms=llms) as client:
        r = client.post("/runs", json={"goal": "Where is my order 1234?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "succeeded" and body["steps"] == 2
    assert body["answer"] == "Your desk lamp has shipped and should arrive on Thursday."
    llm = llms[0]
    assert llm.calls[0]["system"] == main.SYSTEM
    assert [t["name"] for t in llm.calls[0]["tools"]] == ["lookup_order"]
    assert '"eta": "Thursday"' in llm.calls[1]["messages"][-1]["content"]  # the tool result reached the model


def test_background_run_returns_202_then_can_be_polled() -> None:
    with make_client() as client:
        r = client.post("/runs", json={"goal": "Where is my order 1234?", "background": True})
        assert r.status_code == 202
        assert r.json()["status"] == "queued"
        location = r.headers["location"]
        assert location == f"/runs/{r.json()['id']}"
        # TestClient runs background tasks before returning, so the run is already finished here.
        polled = client.get(location).json()
    assert polled["status"] == "succeeded" and "Thursday" in polled["answer"]
    assert polled["finished_at"] >= polled["created_at"]


def test_unknown_run_is_404() -> None:
    with make_client() as client:
        assert client.get("/runs/run_nope").status_code == 404


def test_idempotency_key_prevents_a_second_run() -> None:
    llms: list[MockLLM] = []
    with make_client(llms=llms) as client:
        headers = {"Idempotency-Key": "abc-123"}
        first = client.post("/runs", json={"goal": "Where is my order 1234?"}, headers=headers).json()
        second = client.post("/runs", json={"goal": "Where is my order 1234?"}, headers=headers).json()
        third = client.post("/runs", json={"goal": "Where is my order 1234?"}).json()
    assert first["id"] == second["id"] != third["id"]
    assert len(llms) == 2  # the retried request did not run the agent again


@pytest.mark.parametrize("body", [{"goal": ""}, {}, {"goal": "x" * 4001}, {"goal": 5}])
def test_bad_requests_are_rejected_before_any_model_call(body: dict) -> None:
    llms: list[MockLLM] = []
    with make_client(llms=llms) as client:
        assert client.post("/runs", json=body).status_code == 422
    assert llms == []


def test_failed_run_is_recorded_not_crashed() -> None:
    def broken() -> LLM:
        raise RuntimeError("provider down")

    app = main.create_app(main.Settings(log_level="CRITICAL"), llm_factory=broken)
    with TestClient(app) as client:
        r = client.post("/runs", json={"goal": "Where is my order 1234?"})
        assert r.status_code == 500
        assert r.json()["status"] == "failed" and "provider down" in r.json()["error"]
        assert client.get("/healthz").status_code == 200  # the service itself is fine


def test_deadline_gives_504() -> None:
    settings = main.Settings(log_level="CRITICAL", run_deadline_s=-1)  # already past the deadline
    with make_client(settings) as client:
        r = client.post("/runs", json={"goal": "Where is my order 1234?"})
    assert r.status_code == 504 and r.json()["error"].startswith("DeadlineExceeded")


def test_step_limit_from_settings() -> None:
    looping: Callable[[], LLM] = lambda: MockLLM([MockLLM.tool_call("lookup_order", {"order_id": "1234"})] * 5)  # noqa: E731
    app = main.create_app(main.Settings(log_level="WARNING", max_steps=2), llm_factory=looping)
    with TestClient(app) as client:
        body = client.post("/runs", json={"goal": "loop"}).json()
    assert body["answer"] == "Stopped: step limit reached." and body["steps"] == 2


def test_bearer_token_is_required_when_configured() -> None:
    with make_client(main.Settings(log_level="WARNING", service_token="s3cret")) as client:
        assert client.post("/runs", json={"goal": "hi"}).status_code == 401
        assert client.post("/runs", json={"goal": "hi"}, headers={"Authorization": "Bearer wrong"}).status_code == 401
        ok = client.post("/runs", json={"goal": "hi"}, headers={"Authorization": "Bearer s3cret"})
        assert ok.status_code == 200
        assert client.get("/healthz").status_code == 200  # health checks stay open


def test_settings_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "Mock")
    monkeypatch.setenv("AGENT_MAX_STEPS", "3")
    monkeypatch.setenv("RUN_DEADLINE_SECONDS", "12.5")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("SERVICE_TOKEN_FILE", raising=False)
    s = main.Settings.from_env()
    assert (s.llm_provider, s.max_steps, s.run_deadline_s, s.log_level, s.service_token) == ("mock", 3, 12.5, "DEBUG", None)


def test_secrets_can_be_read_from_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = tmp_path / "anthropic_api_key"
    secret.write_text("sk-test-from-file\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY_FILE", str(secret))
    main.load_secret_files(("ANTHROPIC_API_KEY",))
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-from-file"  # monkeypatch restores it afterwards


def test_logs_are_one_json_object_per_line(caplog: pytest.LogCaptureFixture) -> None:
    with make_client(main.Settings(log_level="INFO")) as client, caplog.at_level(logging.INFO, logger="agent_service"):
        client.post("/runs", json={"goal": "Where is my order 1234?"})
    formatter = main.JsonFormatter()
    entries = [json.loads(formatter.format(rec)) for rec in caplog.records]
    events = [e["event"] for e in entries]
    assert events.index("run.started") < events.index("run.step") < events.index("run.finished") < events.index("http.request")
    finished = next(e for e in entries if e["event"] == "run.finished")
    assert finished["status"] == "succeeded" and "run_id" in finished and "duration_ms" in finished


def test_module_level_app_exists_for_uvicorn() -> None:
    assert {r.path for r in main.app.routes} >= {"/healthz", "/runs", "/runs/{run_id}"}
