# Document Copilot — backend

FastAPI service for retrieval, chat orchestration, and grounded LLM answers.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## First-time setup

```bash
cd backend
cp .env.example .env   # fill in Supabase, DATABASE_URL, OpenAI keys
uv sync
```

Env vars are read from `backend/.env` via `app/config.py` (works regardless of your shell cwd).

## Run (development)

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Or:

```bash
uv run python app/main.py
```

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

## Common commands

| Task | Command |
| ---- | ------- |
| Install / update deps | `uv sync` |
| Add a dependency | `uv add <package>` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check .` |

## Database migrations

Alembic owns database schema changes. SQLAlchemy models live in `app/database/models.py`.

```bash
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "describe change"  # after model edits
```

**Important:** `DATABASE_URL` must use the Supabase **direct** connection (`db.<ref>.supabase.co`), not the pooler. URL-encode special characters in the password (e.g. `@` → `%40`).

Full Alembic workflow: [docs/guides/backend-setup.md](../docs/guides/backend-setup.md)

## Layout

```text
app/
  main.py      # FastAPI entrypoint
  config.py    # settings (single source of truth for env)
  database/    # SQLAlchemy models + metadata
  api/         # routers (added as features land)
```

Full setup: [docs/guides/backend-setup.md](../docs/guides/backend-setup.md)
