# 15 · FastAPI agent service (with Docker)

A small support agent served over HTTP with FastAPI, plus a Dockerfile and a Compose file to run it in a container. Used in [15.6 Deploying with FastAPI & Docker](../../docs/15-production-and-deployment/15.6-deploying-with-fastapi-and-docker.md).

| Endpoint | What it does |
| --- | --- |
| `GET /healthz` | Liveness check. Cheap: never calls the model |
| `POST /runs` with `{"goal": "..."}` | **Sync**: runs the agent and returns the answer (200), or 504 if the run passes its deadline |
| `POST /runs` with `{"goal": "...", "background": true}` | **Async**: returns 202 at once, with the run id and a `Location` header |
| `GET /runs/{run_id}` | The run's status (`queued`, `running`, `succeeded`, `failed`) and answer |

It also shows: config from environment variables (`Settings.from_env`), secrets read from files (`ANTHROPIC_API_KEY_FILE`), one JSON log line per event, a request id on every response, an optional bearer token (`SERVICE_TOKEN`), and an `Idempotency-Key` header so a client retry doesn't start a second run.

| File | Purpose |
| --- | --- |
| `main.py` | The app (`create_app()`), the agent, the demo and `serve` |
| `requirements.txt` | Runtime dependencies for the image only |
| `Dockerfile` | Slim, pinned Python base image; non-root user; health check; no secrets |
| `Dockerfile.dockerignore` | Keeps `.env`, caches and everything else out of the build context |
| `docker-compose.yml` | Builds and runs the image locally, with keys passed in at run time |

## Run it (no server needed)

```bash
cd examples
python 15-fastapi-service/main.py
```

This calls the API in-process with FastAPI's `TestClient`. Output (offline, with `MockLLM`; run ids and the timestamp change on every run):

```text
GET /healthz
  -> 200 {"status": "ok"}
POST /runs {"goal": "Where is my order 1234?"}
  -> 200 {"id": "run_88d713ccfbca", "status": "succeeded", "goal": "Where is my order 1234?", "answer": "Your desk lamp has shipped and should arrive on Thursday.", "error": null, "steps": 2}
POST /runs {"goal": "...", "background": true}  Idempotency-Key: client-req-7
  -> 202 {"id": "run_55a87d6c734b", "status": "queued", "goal": "Where is my order 1234?", "answer": null, "error": null, "steps": 0}
  Location: /runs/run_55a87d6c734b
GET /runs/run_55a87d6c734b
  -> 200 {"id": "run_55a87d6c734b", "status": "succeeded", "goal": "Where is my order 1234?", "answer": "Your desk lamp has shipped and should arrive on Thursday.", "error": null, "steps": 2}
POST the same request again (a client retry)
  -> 200 {"id": "run_55a87d6c734b", "status": "succeeded", "goal": "Where is my order 1234?", "answer": "Your desk lamp has shipped and should arrive on Thursday.", "error": null, "steps": 2}
POST /runs {"goal": ""}
  -> 422 {"detail": [{"type": "string_too_short", "loc": ["body", "goal"], "msg": "String should have at least 1 character", "input": "", "ctx": {"min_length": 1}}]}

One structured log line, as the server writes it:
{"ts": "2026-11-12T20:25:45.471+00:00", "level": "INFO", "event": "run.finished", "run_id": "run_4f1c2a9e0b7d", "status": "succeeded", "duration_ms": 1834.2}
```

## Run a real server

```bash
cd examples/15-fastapi-service
python main.py serve                  # or: uvicorn main:app --reload
curl http://127.0.0.1:8000/healthz
curl -X POST http://127.0.0.1:8000/runs -H "content-type: application/json" -d '{"goal": "Where is my order 1234?"}'
```

FastAPI also serves interactive API docs at <http://127.0.0.1:8000/docs>.

## Run it in Docker

Docker was not available when this example was written, so the image has **not** been built or tested. The files follow the official FastAPI and Docker guidance; if something fails, please open an issue.

```bash
cd examples
docker build -f 15-fastapi-service/Dockerfile -t agent-service .   # context is examples/, for common/
docker run --rm -p 8000:8000 agent-service

# or, from this folder:
cd 15-fastapi-service
docker compose up --build
```

To use a real model, pass the key at run time, never in the image:

```bash
docker run --rm -p 8000:8000 -e LLM_PROVIDER=anthropic -e ANTHROPIC_API_KEY agent-service
```

`-e ANTHROPIC_API_KEY` with no value copies it from your shell. For something safer than environment variables, use the commented `secrets:` section in `docker-compose.yml`: the key is mounted as a file, and the app reads it through `ANTHROPIC_API_KEY_FILE`.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | `mock`, `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | (none) | Provider keys. Or `..._FILE` pointing at a secret file |
| `OPENAI_MODEL` | (none) | Required for `openai` |
| `AGENT_MAX_STEPS` | `6` | Step limit per run |
| `RUN_DEADLINE_SECONDS` | `30` | Give up on a run after this long |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, ... |
| `SERVICE_TOKEN` | (none) | If set, `/runs` needs `Authorization: Bearer <token>` |

## Test it

```bash
cd examples
pytest 15-fastapi-service
```

The tests use `TestClient` and a `MockLLM` factory, so no server starts and no key is needed.

## Limits of this example

- Runs live in memory: they vanish on restart and are not shared between processes. That's why the image runs **one** uvicorn worker. A real service stores runs in a database.
- Background runs use FastAPI's `BackgroundTasks`, which run in the same process after the response. If the process dies, the run is lost. For real background agents, put jobs on a queue and run them in a separate worker ([15.3](../../docs/15-production-and-deployment/15.3-queues-retries-and-idempotency.md), [15.4](../../docs/15-production-and-deployment/15.4-state-persistence-and-resumability.md)).
