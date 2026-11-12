"""An agent as a web service: FastAPI, sync and background runs, a health check, env config and JSON logs.

    python main.py              # offline demo: calls the API in-process with TestClient, no server
    python main.py serve        # start a real server on http://127.0.0.1:8000 (docs at /docs)
    uvicorn main:app            # the same, the way the Docker image starts it

Read alongside docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md.

Endpoints:
    GET  /healthz          liveness check for Docker, Kubernetes or a load balancer
    POST /runs             {"goal": "...", "background": false}  -> 200 with the answer
                           {"goal": "...", "background": true}   -> 202 with a run id
    GET  /runs/{run_id}    the run's status and, when finished, its answer

The run store is in memory, to keep the example small. A real deployment keeps
runs in a database and does background work in a separate worker process fed by
a queue (see 15.1 and 15.3), so runs survive restarts and work with many replicas.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import threading
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from common import LLM, LLMResponse, Message, MockLLM, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- configuration from the environment


@dataclass(frozen=True)
class Settings:
    """Everything that changes between laptop, staging and production comes from environment variables."""

    llm_provider: str = "mock"  # LLM_PROVIDER: mock | anthropic | openai
    max_steps: int = 6  # AGENT_MAX_STEPS
    run_deadline_s: float = 30.0  # RUN_DEADLINE_SECONDS: give up on a run after this long
    log_level: str = "INFO"  # LOG_LEVEL
    service_token: str | None = None  # SERVICE_TOKEN: if set, POST/GET /runs need "Authorization: Bearer <token>"

    @classmethod
    def from_env(cls) -> Settings:
        try:
            from dotenv import load_dotenv

            load_dotenv()  # local development only; never copy a .env file into an image
        except ImportError:
            pass
        load_secret_files()
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "6")),
            run_deadline_s=float(os.getenv("RUN_DEADLINE_SECONDS", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            service_token=os.getenv("SERVICE_TOKEN") or None,
        )


SECRET_NAMES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERVICE_TOKEN")


def load_secret_files(names: tuple[str, ...] = SECRET_NAMES) -> None:
    """Support the `NAME_FILE` convention used with Docker and Kubernetes secrets.

    Secrets are often mounted as files (e.g. /run/secrets/anthropic_api_key) rather
    than set as plain environment variables. If NAME is unset and NAME_FILE points
    to a file, read the file into NAME so the SDKs find it as usual.
    """
    for name in names:
        path = os.getenv(f"{name}_FILE")
        if path and not os.getenv(name):
            os.environ[name] = Path(path).read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------- structured (JSON) logs


class JsonFormatter(logging.Formatter):
    """One JSON object per line: easy to search and to ship to any log platform."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


log = logging.getLogger("agent_service")


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log.handlers = [handler]
    log.setLevel(level)


def log_event(event: str, **fields: Any) -> None:
    """Log an event name plus fields. Never put secrets or full prompts here."""
    log.info(event, extra={"fields": fields})


# --------------------------------------------------------------------------- the agent (small on purpose)

ORDERS = {"1234": {"item": "desk lamp", "status": "shipped", "eta": "Thursday"}}

LOOKUP_SPEC: ToolSpec = {
    "name": "lookup_order",
    "description": "Look up an order by its 4-digit id. Returns item, status and estimated delivery day.",
    "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
}
SYSTEM = "You are a customer support agent. Use lookup_order for order questions; never guess. Answer in one sentence."


def lookup_order(order_id: str) -> str:
    order = ORDERS.get(order_id)
    return json.dumps(order) if order else f"Error: no order {order_id}"


def support_mock(messages: list[Message]) -> LLMResponse | str:
    """A scripted model for offline runs: look the order up, then answer from the tool result."""
    results = [m for m in messages if m["role"] == "tool"]
    if not results:
        words = [w.strip("?.,!") for w in messages[0]["content"].split()]
        order_id = next((w for w in words if w.isdigit() and len(w) == 4), None)
        if order_id is None:
            return "Which order is this about? Please give me the 4-digit order number."
        return MockLLM.tool_call("lookup_order", {"order_id": order_id})
    if results[-1]["content"].startswith("Error"):
        return "I couldn't find that order. Could you check the number?"
    order = json.loads(results[-1]["content"])
    return f"Your {order['item']} has {order['status']} and should arrive on {order['eta']}."


class DeadlineExceeded(Exception):
    """The run took longer than RUN_DEADLINE_SECONDS."""


def run_agent(llm: LLM, goal: str, *, run_id: str, max_steps: int, deadline_s: float) -> tuple[str, int]:
    """The agent loop. Returns (answer, steps used). Checks the deadline before every model call."""
    started = time.monotonic()
    messages: list[Message] = [user(goal)]
    for step in range(1, max_steps + 1):
        if time.monotonic() - started > deadline_s:
            raise DeadlineExceeded(f"deadline of {deadline_s}s passed after {step - 1} steps")
        reply = llm.chat(messages, system=SYSTEM, tools=[LOOKUP_SPEC])
        log_event("run.step", run_id=run_id, step=step, tools=[c.name for c in reply.tool_calls],
                  input_tokens=reply.usage.input_tokens, output_tokens=reply.usage.output_tokens)
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text, step
        for call in reply.tool_calls:
            out = lookup_order(**call.arguments) if call.name == "lookup_order" else f"Error: unknown tool {call.name}"
            messages.append(tool_result(call.id, out, is_error=out.startswith("Error")))
    return "Stopped: step limit reached.", max_steps


# --------------------------------------------------------------------------- run storage (in memory, for the example)

Status = Literal["queued", "running", "succeeded", "failed"]


class RunStore:
    """Thread-safe in-memory runs. Lost on restart and NOT shared between worker processes."""

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._by_key: dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, goal: str, idempotency_key: str | None) -> tuple[dict[str, Any], bool]:
        """Create a run, or return the existing one if this idempotency key was seen before."""
        with self._lock:
            if idempotency_key and idempotency_key in self._by_key:
                return dict(self._runs[self._by_key[idempotency_key]]), False
            run = {"id": f"run_{uuid.uuid4().hex[:12]}", "status": "queued", "goal": goal, "answer": None,
                   "error": None, "steps": 0, "created_at": time.time(), "finished_at": None}
            self._runs[run["id"]] = run
            if idempotency_key:
                self._by_key[idempotency_key] = run["id"]
            return dict(run), True

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            run = self._runs.get(run_id)
            return dict(run) if run else None

    def update(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            self._runs[run_id].update(fields)


# --------------------------------------------------------------------------- the HTTP API


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000, description="What the agent should do.")
    background: bool = Field(False, description="false: wait for the answer. true: return 202 at once and poll.")


class RunView(BaseModel):
    id: str
    status: Status
    goal: str
    answer: str | None = None
    error: str | None = None
    steps: int = 0
    created_at: float
    finished_at: float | None = None


def create_app(settings: Settings | None = None, llm_factory: Callable[[], LLM] | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings and a MockLLM factory; production reads the environment."""
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)
    make_llm = llm_factory or (lambda: get_llm(settings.llm_provider, mock_responses=[support_mock] * (settings.max_steps + 1)))
    store = RunStore()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        log_event("service.started", provider=settings.llm_provider, max_steps=settings.max_steps)
        yield
        log_event("service.stopping")  # in-flight background tasks die with the process: another reason for a queue

    app = FastAPI(title="Agent service", version="1.0.0", lifespan=lifespan)
    app.state.store = store

    def require_token(authorization: str | None = Header(default=None)) -> None:
        if settings.service_token is None:
            return
        expected = f"Bearer {settings.service_token}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="missing or wrong bearer token")

    @app.middleware("http")
    async def access_log(request: Request, call_next: Callable[..., Any]) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        log_event("http.request", request_id=request_id, method=request.method, path=request.url.path,
                  status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 1))
        return response

    def execute(run_id: str) -> None:
        """Run the agent for one stored run and record the outcome. Never raises."""
        run = store.get(run_id)
        assert run is not None
        store.update(run_id, status="running")
        log_event("run.started", run_id=run_id)
        started = time.perf_counter()
        try:
            answer, steps = run_agent(make_llm(), run["goal"], run_id=run_id,
                                      max_steps=settings.max_steps, deadline_s=settings.run_deadline_s)
            store.update(run_id, status="succeeded", answer=answer, steps=steps, finished_at=time.time())
        except Exception as exc:  # a failed run is data, not a crash of the service
            store.update(run_id, status="failed", error=f"{type(exc).__name__}: {exc}", finished_at=time.time())
            log.exception("run.error", extra={"fields": {"run_id": run_id}})
        log_event("run.finished", run_id=run_id, status=store.get(run_id)["status"],  # type: ignore[index]
                  duration_ms=round((time.perf_counter() - started) * 1000, 1))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness: the process is up and serving. Keep it cheap: never call the model here."""
        return {"status": "ok"}

    @app.post("/runs", response_model=RunView, dependencies=[Depends(require_token)],
              responses={202: {"model": RunView}, 504: {"model": RunView}})
    def create_run(body: RunRequest, background_tasks: BackgroundTasks, response: Response,
                   idempotency_key: str | None = Header(default=None)) -> RunView:
        # A plain `def` (not `async def`): FastAPI runs it in a thread pool, so slow,
        # blocking model calls don't freeze the server for everyone else.
        run, created = store.create(body.goal, idempotency_key)
        if not created:
            return RunView(**run)  # a client retry with the same Idempotency-Key: no second run
        if body.background:
            background_tasks.add_task(execute, run["id"])  # runs after the 202 is sent
            response.status_code = 202
            response.headers["Location"] = f"/runs/{run['id']}"
            return RunView(**run)
        execute(run["id"])
        run = store.get(run["id"]) or run
        if run["status"] == "failed":
            response.status_code = 504 if (run["error"] or "").startswith("DeadlineExceeded") else 500
        return RunView(**run)

    @app.get("/runs/{run_id}", response_model=RunView, dependencies=[Depends(require_token)])
    def get_run(run_id: str) -> RunView:
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"no run {run_id}")
        return RunView(**run)

    return app


app = create_app()  # what `uvicorn main:app` serves


# --------------------------------------------------------------------------- demo


def demo() -> None:
    """Call the API in-process with TestClient (needs httpx). No server, no network."""
    from fastapi.testclient import TestClient

    with TestClient(create_app(Settings(log_level="WARNING"))) as client:  # quiet logs, readable demo
        def show(label: str, r: Any) -> None:
            body = {k: v for k, v in r.json().items() if k not in ("created_at", "finished_at")}
            print(f"{label}\n  -> {r.status_code} {json.dumps(body)}")

        show("GET /healthz", client.get("/healthz"))
        show('POST /runs {"goal": "Where is my order 1234?"}',
             client.post("/runs", json={"goal": "Where is my order 1234?"}))
        r = client.post("/runs", json={"goal": "Where is my order 1234?", "background": True},
                        headers={"Idempotency-Key": "client-req-7"})
        show('POST /runs {"goal": "...", "background": true}  Idempotency-Key: client-req-7', r)
        print(f"  Location: {r.headers['location']}")
        show(f"GET {r.headers['location']}", client.get(r.headers["location"]))
        show("POST the same request again (a client retry)",
             client.post("/runs", json={"goal": "Where is my order 1234?", "background": True},
                         headers={"Idempotency-Key": "client-req-7"}))
        show('POST /runs {"goal": ""}', client.post("/runs", json={"goal": ""}))

    print("\nOne structured log line, as the server writes it:")
    configure_logging("INFO")
    log_event("run.finished", run_id="run_4f1c2a9e0b7d", status="succeeded", duration_ms=1834.2)


def serve() -> None:
    import uvicorn

    # access_log=False: our middleware already writes one JSON line per request
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), access_log=False)


if __name__ == "__main__":
    serve() if sys.argv[1:] == ["serve"] else demo()
