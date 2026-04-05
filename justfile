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

# Build all Docker images
build:
    docker compose build

# Build with no cache
build-fresh:
    docker compose build --no-cache

# Remove all containers and volumes (DESTRUCTIVE)
clean:
    docker compose down -v --remove-orphans

# Push images to registry (set REGISTRY env var)
push registry="":
    #!/usr/bin/env bash
    REG="{{ registry }}"
    if [ -z "$REG" ]; then
        echo "Usage: just push <registry>"
        exit 1
    fi
    docker tag ticketsystem-backend "$REG/ticketsystem-backend:latest"
    docker tag ticketsystem-frontend "$REG/ticketsystem-frontend:latest"
    docker push "$REG/ticketsystem-backend:latest"
    docker push "$REG/ticketsystem-frontend:latest"

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

# Create superuser (interactive)
create-superuser: backend-migrate
    cd backend && UV_PYTHON=3.13 uv run python scripts/create_superuser.py
