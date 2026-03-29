# TicketSystem

A web-based ticket system with Kanban board, drag-and-drop, user auth (with 2FA support), and a shared REST API backend for web and mobile.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic |
| Frontend | React 18, TypeScript, Vite, @dnd-kit, TanStack Query, Zustand |
| Mobile | React Native (Expo) — same backend API |
| Database | SQLite (swappable via `DATABASE_URL`) |
| Container | Docker / Podman (docker-compose) |
| CI | GitHub Actions |

## Project Structure

```
ticketsystem/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth.py, tickets.py, users.py
│   │   ├── core/               # config, security, deps, exceptions
│   │   ├── db/                 # session, Base
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # business logic (user, ticket, totp)
│   │   └── tests/              # pytest unit + integration tests
│   ├── alembic/                # Database migrations
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── api/                # Axios API client & endpoints
│   │   ├── components/
│   │   │   ├── auth/           # LoginPage, RegisterPage
│   │   │   ├── board/          # KanbanBoard, KanbanColumn, TicketCard
│   │   │   ├── tickets/        # TicketDetail, CreateTicketModal
│   │   │   └── common/         # Navbar
│   │   ├── hooks/              # TanStack Query hooks
│   │   ├── store/              # Zustand auth store
│   │   ├── styles/             # globals.css
│   │   └── types/              # TypeScript types
│   ├── Dockerfile
│   └── package.json
│
├── mobile/                     # React Native (Expo)
│   ├── src/
│   │   ├── api/                # Mobile API client (SecureStore tokens)
│   │   ├── screens/            # TicketListScreen
│   │   └── types/
│   └── app.json
│
├── docker-compose.yml          # Production
├── docker-compose.dev.yml      # Development (hot-reload)
└── justfile                    # Task runner
```

## Quick Start

### Prerequisites
- [just](https://github.com/casey/just) — task runner
- Docker / Podman + docker-compose (or podman-compose)

### Development

```bash
# Install dependencies
just install

# Start dev stack (hot-reload on both backend and frontend)
just dev

# App runs at:
#   Frontend: http://localhost:3000
#   Backend API: http://localhost:8000
#   API docs: http://localhost:8000/api/docs
```

### Production

```bash
# Start production stack
just up

# App runs at:
#   http://localhost:8080
```

### Running with Podman

```bash
# Works the same as Docker
just podman-up
```

## Available Commands (`just`)

| Command | Description |
|---|---|
| `just dev` | Start dev stack with hot-reload |
| `just up` | Start production stack |
| `just down` | Stop containers |
| `just test` | Run all tests |
| `just check` | Lint + typecheck + test |
| `just backend-test` | Backend tests only |
| `just frontend-test` | Frontend tests only |
| `just backend-lint` | Run ruff linter |
| `just backend-migrate` | Apply DB migrations |
| `just backend-migration <name>` | Create a new migration |
| `just hooks-install` | Install pre-commit hooks |
| `just hooks-run` | Run pre-commit on all files |
| `just create-superuser` | Interactive superuser creation |

## Ticket Statuses

```
New (ToDo) → Working → Waiting → Resolved → Closed
```

Every status change is recorded in the `StatusLog` table with:
- Who changed it
- Previous status → new status
- Optional note

## API Documentation

Swagger UI: `http://localhost:8000/api/docs`
ReDoc: `http://localhost:8000/api/redoc`

## Authentication

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → returns `access_token` + `refresh_token`
3. **Refresh**: `POST /api/v1/auth/refresh`
4. **2FA Setup**: `POST /api/v1/auth/totp/setup` → returns QR code
5. **2FA Verify**: `POST /api/v1/auth/totp/verify` → enables TOTP
6. Login with TOTP: include `totp_code` field in login request

## Database Swap

Change `DATABASE_URL` env var:
- **SQLite**: `sqlite+aiosqlite:///./ticketsystem.db`
- **PostgreSQL**: `postgresql+asyncpg://user:pass@host/dbname`
- **MySQL**: `mysql+aiomysql://user:pass@host/dbname`

## Mobile App (React Native / Expo)

The mobile app uses the same REST API. Tokens are stored securely via `expo-secure-store`.

```bash
just mobile-install
just mobile-start    # Expo dev server
just mobile-android  # Android emulator
just mobile-ios      # iOS simulator
```

## Code Quality

- **Ruff** — Python linting + formatting
- **mypy** — Python type checking
- **ESLint** — TypeScript/React linting
- **pre-commit** — Git hooks (install with `just hooks-install`)
- **pytest** — Backend testing (unit + integration, SQLite in-memory)
- **vitest** — Frontend testing with jsdom
# schirrmeisterei
