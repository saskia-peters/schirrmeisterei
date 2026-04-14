# Development Guide

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.13 |
| uv | ≥ 0.11 |
| Node.js | ≥ 20 LTS |
| pnpm | 10.33.0 |
| just | ≥ 1.27 |
| Podman | ≥ 4 (Docker also supported) |

---

## Backend Setup

```bash
just backend-install        # install dependencies into backend/.venv
just db-start               # start PostgreSQL container
just backend-migrate        # run Alembic migrations
just backend-run            # start uvicorn on :8000 with hot-reload
```

Or start the full stack (backend + frontend + Postgres) in one command:

```bash
just dev
```

### Running tests

Tests use an in-memory SQLite database — no running Postgres needed:

```bash
# Unit tests (fast, in-memory SQLite)
just backend-test-unit

# Integration tests (HTTP-level, still in-memory SQLite)
just backend-test-integration

# All backend tests
just backend-test

# All backend tests with HTML + terminal coverage report
just backend-test-cov
```

#### Test architecture

| Layer | Location | Adapter |
|-------|----------|---------|
| Unit | `app/tests/unit/` | SQLite in-memory via `aiosqlite` |
| Integration | `app/tests/integration/` | SQLite in-memory + `httpx.AsyncClient` |

The `conftest.py` creates a fresh in-memory SQLite schema for each test function and tears it down afterwards, so tests are completely isolated.

---

## Frontend Setup

```bash
just frontend-install       # pnpm install
just frontend-run           # Vite dev server on http://localhost:5173
```

### Running tests

```bash
just frontend-test-run      # single run (default, used in CI)
just frontend-test          # vitest watch mode
just frontend-test-cov      # with coverage
```

#### Test architecture

| Layer | Location | Adapter |
|-------|----------|---------|
| Unit | `src/components/**/__tests__/*.test.tsx` | `vi.mock('@/api', ...)` — no network |
| Integration | (future) | Real `apiClient` against running backend |

All component tests use `vi.mock` to replace the API and hook layers with in-memory stubs, making them fast and deterministic.

---

## Adding a Migration

```bash
# Generate a new migration from model changes
just backend-migration "describe change"

# Apply all pending migrations
just backend-migrate

# Roll back one step
just backend-downgrade

# Reset the DB (drop schema → re-migrate → ready for seeding)
just db-reset
```

---

## Email Ingestion

The IMAP poller runs as a background asyncio task inside the FastAPI lifespan. It is only started when `IMAP_ENABLED=true`.

### Testing locally

The admin endpoint triggers a single poll without waiting for the interval:

```bash
curl -X POST http://localhost:8000/api/v1/admin/email-ingestion/poll \
  -H "Authorization: Bearer <superuser_token>"
# returns: {"processed": 1, "skipped": 0, "errors": 0, "error_details": []}
```

### Key files

| File | Purpose |
|------|---------|
| `app/services/email_ingestion.py` | RFC 2822 parsing, subject matching, comment + attachment persistence |
| `app/services/imap_poller.py` | IMAP connection, UNSEEN fetch loop, `poll_once()` / `run_forever()` |

### Subject format

Only bracket notation is accepted to avoid false positives:

```
[Ticket #42]  ← preferred
[Ticket-42]
[Ticket 42]
```

---

## Code Style

- **Backend**: `ruff` (lint + format), `mypy` (type checking)
- **Frontend**: ESLint + TypeScript strict mode

```bash
# Backend — lint, format-check, type-check, test
just backend-check

# Backend — individual steps
just backend-lint
just backend-format
just backend-typecheck

# Frontend — lint, type-check, test
just frontend-check

# Both — full quality gate
just check
```
