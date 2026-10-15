# Brain (FastAPI)

The CookToFit backend: the conversation core, domain services, WhatsApp webhook and background jobs. In Phase 0 it only exposes health endpoints.

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness check. Never touches dependencies. |
| `GET /readyz` | Readiness check. Runs `select 1` against Postgres; returns 503 if the database is unreachable. |
