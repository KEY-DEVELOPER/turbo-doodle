# EdgeLedger

Football (soccer) +EV research, decision-support and tracking web app. It does not place bets,
hold money or store bookmaker passwords. Source of truth: `tasks/prd-edgeledger-ev-research-suite.md`.
Agent rules: `CLAUDE.md`. Decisions: `docs/decisions/`.

```
backend/    FastAPI modular monolith (Python 3.12, SQLAlchemy 2, Alembic, Pydantic v2)
frontend/   Next.js 16 + TypeScript
tools/      Repo tooling (RG-08 banned-terms linter)
docs/decisions/  ADRs
tests/e2e/  End-to-end tests (later)
```

## Local development

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you),
Node.js 22 (`frontend/.nvmrc`).

```bash
# 0. Config (dev-only values; .env is git-ignored)
cp .env.example .env

# 1. Infrastructure: Postgres 16, Redis, MinIO (+ bucket)
docker compose up -d
#    Ports busy? Override in .env: POSTGRES_PORT, REDIS_PORT, MINIO_PORT, MINIO_CONSOLE_PORT
#    and update EDGELEDGER_*_URL to match. MinIO console: http://localhost:9001

# 2. Backend
cd backend
uv sync                                   # creates .venv with Python 3.12 + dev tools
uv run alembic upgrade head               # apply migrations
uv run uvicorn app.main:app --reload      # http://localhost:8000/health, docs at /docs

# 3. Frontend (new terminal)
cd frontend
npm ci
npm run dev                               # http://localhost:3000
```

### Checks (same as CI)

```bash
# backend/
uv run ruff check . ../tools && uv run ruff format --check . ../tools
uv run mypy app
uv run lint-imports                       # module boundaries (CLAUDE.md §4)
uv run alembic check                      # ORM models match migrations
uv run pytest -q                          # DB tests need Postgres (see below)

# repo root
python3 tools/banned_terms.py             # RG-08 banned terms (EN + IT)

# frontend/
npm run lint && npm run typecheck && npm test
```

DB tests create and drop a throwaway database per run on the server in
`EDGELEDGER_TEST_DATABASE_URL` (default `...@localhost:5432/postgres`), so parallel worktrees do
not collide. Without a reachable server they are skipped locally; CI sets
`EDGELEDGER_REQUIRE_DB=1` so they always run there.

### Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "<req_id>_<short_desc>"   # e.g. led01_ledger_accounts
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
```

Register new model modules in `backend/app/all_models.py`. Append-only / bitemporal tables
attach the shared DB guards from `app/core/ddl.py` in their migration.

### API client

```bash
cd backend && uv run python -m app.api.openapi_export ../frontend/openapi.json
cd ../frontend && npm run gen:api
```
Commit both files; CI fails if they are stale.
