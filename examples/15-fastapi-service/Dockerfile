# syntax=docker/dockerfile:1
#
# Build from the examples/ folder, because the service imports the shared `common` package:
#     cd examples
#     docker build -f 15-fastapi-service/Dockerfile -t agent-service .
#     docker run --rm -p 8000:8000 agent-service
# Or use docker-compose.yml in this folder.

# A slim official Python image, pinned to an exact version so builds are repeatable.
# For fully reproducible builds, pin the digest too: python:3.13.18-slim-trixie@sha256:...
FROM python:3.13.18-slim-trixie

# Don't write .pyc files, don't buffer stdout (logs appear at once), keep pip quiet and cache-free.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY 15-fastapi-service/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Then the code. main.py adds its parent's parent (/app) to sys.path to find `common`.
COPY common/ /app/common/
COPY 15-fastapi-service/main.py /app/service/main.py

# Run as an unprivileged user, never as root.
RUN useradd --create-home --uid 10001 appuser
USER appuser
WORKDIR /app/service

# Non-secret defaults. Secrets (API keys) are passed at run time, never baked in.
ENV LLM_PROVIDER=mock \
    AGENT_MAX_STEPS=6 \
    RUN_DEADLINE_SECONDS=30 \
    LOG_LEVEL=INFO

EXPOSE 8000

# Docker marks the container unhealthy if /healthz stops answering.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

# One worker process: the example keeps runs in memory, which workers would not share.
# Exec form (JSON array) so uvicorn gets SIGTERM directly and shuts down cleanly.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
