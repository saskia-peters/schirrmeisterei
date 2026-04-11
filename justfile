# TicketSystem - justfile
# Run `just` to see available commands

set dotenv-load := true
set shell := ["bash", "-c"]

# Default: list all commands
default:
    @just --list

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

# Start full stack in development mode (hot-reload)
dev:
    podman compose -f docker-compose.dev.yml up

# Start full stack in production mode
up:
    podman compose up --build

# Stop all containers
down:
    podman compose down

# Stop dev containers
dev-down:
    podman compose -f docker-compose.dev.yml down

# View logs
logs service="":
    #!/usr/bin/env bash
    if [ -z "{{ service }}" ]; then
        podman compose logs -f
    else
        podman compose logs -f {{ service }}
    fi

# ─────────────────────────────────────────────────────────────────────────────
# Database (PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

# Start only the PostgreSQL container (for local backend dev without full stack)
db-start:
    #!/usr/bin/env bash
    if podman container exists ticketsystem-postgres-dev; then
        podman start ticketsystem-postgres-dev
    else
        podman compose -f docker-compose.dev.yml up -d postgres
    fi

# Stop and remove the PostgreSQL container
db-stop:
    podman compose -f docker-compose.dev.yml stop postgres

# Open a psql shell in the running dev postgres container
db-shell:
    podman exec -it ticketsystem-postgres-dev psql -U ticketsystem -d ticketsystem

# Reset the database: drop and recreate schema, then re-run migrations
db-reset: db-start
    #!/usr/bin/env bash
    echo "Waiting for postgres to be ready..."
    until podman exec ticketsystem-postgres-dev pg_isready -U ticketsystem -d ticketsystem; do
        sleep 1
    done
    podman exec ticketsystem-postgres-dev psql -U ticketsystem -d ticketsystem \
        -c "DROP SCHEMA IF EXISTS ticketsystem CASCADE; CREATE SCHEMA ticketsystem;"
    cd backend && UV_PYTHON=3.13 uv run alembic upgrade head
    echo "Database reset complete."

# ─────────────────────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────────────────────

# Install backend dependencies
backend-install:
    cd backend && UV_PYTHON=3.13 uv sync

# Run backend locally (without Podman)
backend-run:
    cd backend && UV_PYTHON=3.13 uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
backend-migrate:
    cd backend && UV_PYTHON=3.13 uv run alembic upgrade head

# Create new migration
backend-migration name:
    cd backend && UV_PYTHON=3.13 uv run alembic revision --autogenerate -m "{{ name }}"

# Downgrade migration
backend-downgrade:
    cd backend && UV_PYTHON=3.13 uv run alembic downgrade -1

# Run backend tests
backend-test:
    cd backend && UV_PYTHON=3.13 uv run pytest

# Run only backend unit tests
backend-test-unit:
    cd backend && UV_PYTHON=3.13 uv run pytest app/tests/unit/ -v

# Run only backend integration tests
backend-test-integration:
    cd backend && UV_PYTHON=3.13 uv run pytest app/tests/integration/ -v

# Run backend tests with coverage
backend-test-cov:
    cd backend && UV_PYTHON=3.13 uv run pytest --cov=app --cov-report=html --cov-report=term

# Run backend linter (ruff)
backend-lint:
    cd backend && UV_PYTHON=3.13 uv run ruff check .

# Fix backend lint issues
backend-lint-fix:
    cd backend && UV_PYTHON=3.13 uv run ruff check . --fix

# Run backend formatter
backend-format:
    cd backend && UV_PYTHON=3.13 uv run ruff format .

# Run backend type checker
backend-typecheck:
    cd backend && UV_PYTHON=3.13 uv run mypy app/

# Run all backend quality checks
backend-check: backend-lint backend-typecheck backend-test

# ─────────────────────────────────────────────────────────────────────────────
# Frontend
# ─────────────────────────────────────────────────────────────────────────────

# Install frontend dependencies
frontend-install:
    cd frontend && pnpm install

# Run frontend dev server locally
frontend-run:
    cd frontend && pnpm run dev

# Build frontend for production
frontend-build:
    cd frontend && pnpm run build

# Run frontend tests
frontend-test:
    cd frontend && pnpm test

# Run frontend tests once (no watch mode)
frontend-test-run:
    cd frontend && pnpm test --run

# Run frontend tests with coverage
frontend-test-cov:
    cd frontend && pnpm run test:coverage

# Run frontend linter
frontend-lint:
    cd frontend && pnpm run lint

# Type check frontend
frontend-typecheck:
    cd frontend && pnpm run typecheck

# Run all frontend quality checks
frontend-check: frontend-lint frontend-typecheck frontend-test

# ─────────────────────────────────────────────────────────────────────────────
# Full Stack
# ─────────────────────────────────────────────────────────────────────────────

# Install all dependencies
install: backend-install frontend-install

# Run all tests (backend + frontend)
test: backend-test frontend-test

# Run all unit tests
test-unit: backend-test-unit

# Run all integration tests
test-integration: backend-test-integration

# Run all quality checks
check: backend-check frontend-check

# ─────────────────────────────────────────────────────────────────────────────
# Pre-commit (prek)
# ─────────────────────────────────────────────────────────────────────────────

# Install prek git hooks
hooks-install:
    prek install

# Run prek on all files
hooks-run:
    prek -a

# ─────────────────────────────────────────────────────────────────────────────
# Docker / Podman
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY := "ghcr.io/saskia-peters"

# Build all Docker images
build:
    podman compose build

# Build with no cache
build-fresh:
    podman compose build --no-cache

# Remove all containers and volumes (DESTRUCTIVE)
clean:
    podman compose down -v --remove-orphans

# Build, tag, and push images to GHCR (login first: podman login ghcr.io)
package version="latest":
    #!/usr/bin/env bash
    set -euo pipefail
    TAG="{{ version }}"
    echo "Building images..."
    podman build -t schirrmeisterei-backend:"$TAG"  backend/
    podman build -t schirrmeisterei-frontend:"$TAG" frontend/
    echo "Tagging for {{ REGISTRY }}..."
    podman tag schirrmeisterei-backend:"$TAG"  {{ REGISTRY }}/schirrmeisterei-backend:"$TAG"
    podman tag schirrmeisterei-frontend:"$TAG" {{ REGISTRY }}/schirrmeisterei-frontend:"$TAG"
    echo "Pushing to {{ REGISTRY }}..."
    podman push {{ REGISTRY }}/schirrmeisterei-backend:"$TAG"
    podman push {{ REGISTRY }}/schirrmeisterei-frontend:"$TAG"
    if [ "$TAG" != "latest" ]; then
        podman tag schirrmeisterei-backend:"$TAG"  {{ REGISTRY }}/schirrmeisterei-backend:latest
        podman tag schirrmeisterei-frontend:"$TAG" {{ REGISTRY }}/schirrmeisterei-frontend:latest
        podman push {{ REGISTRY }}/schirrmeisterei-backend:latest
        podman push {{ REGISTRY }}/schirrmeisterei-frontend:latest
    fi
    echo "Done. Images pushed:"
    echo "  {{ REGISTRY }}/schirrmeisterei-backend:$TAG"
    echo "  {{ REGISTRY }}/schirrmeisterei-frontend:$TAG"

# Push images to registry (set REGISTRY env var)
push registry="":
    #!/usr/bin/env bash
    REG="{{ registry }}"
    if [ -z "$REG" ]; then
        echo "Usage: just push <registry>"
        exit 1
    fi
    podman tag ticketsystem-backend "$REG/ticketsystem-backend:latest"
    podman tag ticketsystem-frontend "$REG/ticketsystem-frontend:latest"
    podman push "$REG/ticketsystem-backend:latest"
    podman push "$REG/ticketsystem-frontend:latest"

# Run with podman-compose (alternative to docker compose)
podman-up:
    podman-compose up --build

podman-down:
    podman-compose down

# ─────────────────────────────────────────────────────────────────────────────
# Mobile (React Native)
# ─────────────────────────────────────────────────────────────────────────────

# Install mobile dependencies
mobile-install:
    cd mobile && npm install

# Start mobile dev server
mobile-start:
    cd mobile && npx expo start

# Run on Android
mobile-android:
    cd mobile && npx expo run:android

# Run on iOS
mobile-ios:
    cd mobile && npx expo run:ios

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

# Show project structure
tree:
    find . -not -path '*/node_modules/*' -not -path '*/.git/*' \
           -not -path '*/__pycache__/*' -not -path '*/.venv/*' \
           -not -path '*/dist/*' -not -path '*/htmlcov/*' | sort

# Initialise the database: generate data files, run migrations, create superuser
init-db: db-start
    cd backend && UV_PYTHON=3.13 uv run python scripts/init_db.py

# ─────────────────────────────────────────────────────────────────────────────
# Documentation (MkDocs)
# ─────────────────────────────────────────────────────────────────────────────

# Build MkDocs documentation (output goes to docs/)
docs-build:
    cd assets/mkdocs && mkdocs build

# Serve MkDocs documentation locally with live-reload
docs-serve:
    cd assets/mkdocs && mkdocs serve --dev-addr=127.0.0.1:8001
