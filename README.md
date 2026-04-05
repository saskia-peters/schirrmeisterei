# Schirrmeisterei

A web-based ticket system with Kanban board, drag-and-drop, role-based permissions, user auth (with 2FA), and a shared REST API for web and mobile.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2 (async), Alembic, PyJWT |
| Frontend | React 18, TypeScript, Vite 6, @dnd-kit, TanStack Query v5, Zustand, Sonner |
| Mobile | React Native (Expo) — same backend API |
| Database | SQLite (swappable via `DATABASE_URL`) |
| Container | Podman / Docker (compose) |
| Hooks | [prek](https://github.com/walterbm/prek) (Rust-based pre-commit) |

## Project Structure

```
ticketsystem/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth.py, tickets.py, users.py, admin.py
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
│   │   │   ├── admin/          # AdminPanel (priorities, categories, user roles)
│   │   │   ├── auth/           # LoginPage, RegisterPage
│   │   │   ├── board/          # KanbanBoard, KanbanColumn, TicketCard
│   │   │   ├── tickets/        # TicketDetail, CreateTicketModal
│   │   │   └── common/         # Navbar
│   │   ├── hooks/              # TanStack Query hooks
│   │   ├── store/              # Zustand auth store
│   │   ├── styles/             # globals.css
│   │   └── types/              # TypeScript types
│   ├── eslint.config.js        # ESLint 9 flat config
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
├── .pre-commit-config.yaml     # prek hook configuration
├── docker-compose.yml          # Production
├── docker-compose.dev.yml      # Development (hot-reload)
└── justfile                    # Task runner
```

## Quick Start

### Prerequisites

- [just](https://github.com/casey/just) — task runner
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [prek](https://github.com/walterbm/prek) — pre-commit hook runner (`cargo install prek`)
- Podman + podman-compose (or Docker + docker-compose)

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
just up

# App runs at:
#   http://localhost:8080
```

### Install git hooks

```bash
just hooks-install
```

## Available Commands (`just`)

| Command | Description |
|---|---|
| `just dev` | Start dev stack with hot-reload |
| `just up` | Start production stack |
| `just down` | Stop containers |
| `just dev-down` | Stop dev containers |
| `just install` | Install all dependencies |
| `just test` | Run all tests |
| `just check` | Lint + typecheck + test |
| `just backend-run` | Run backend locally (no container) |
| `just backend-test` | Backend tests only (pytest) |
| `just backend-lint` | Run ruff linter |
| `just backend-lint-fix` | Run ruff with auto-fix |
| `just backend-format` | Run ruff formatter |
| `just backend-typecheck` | Run mypy |
| `just backend-migrate` | Apply DB migrations |
| `just backend-migration <name>` | Create a new migration |
| `just frontend-run` | Run frontend locally (no container) |
| `just frontend-test` | Frontend tests only (vitest) |
| `just frontend-lint` | Run ESLint |
| `just frontend-typecheck` | Run tsc --noEmit |
| `just hooks-install` | Install prek git hooks |
| `just hooks-run` | Run prek on all files |
| `just create-superuser` | Interactive superuser creation |
| `just logs [service]` | Tail container logs |

## User Roles

Every user is assigned to one or more groups that control permissions:

| Group | Permissions |
|---|---|
| `helfende` | Default group — create, view, update tickets |
| `schirrmeister` | All of the above + close tickets |
| `admin` | Full access including user role management |

Superusers (created via `just create-superuser`) are automatically placed in the `admin` group.

## Ticket Statuses

```
New (ToDo) → Working → Waiting → Resolved → Closed
```

- Moving to **Waiting** requires a "Waiting for" note explaining the reason.
- Moving to **Closed** requires `schirrmeister` or `admin` group membership.
- Every status change is recorded in the `StatusLog` table (who, from, to, note).

## Authentication

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → returns `access_token` + `refresh_token`
3. **Refresh**: `POST /api/v1/auth/refresh`
4. **2FA Setup**: `POST /api/v1/auth/totp/setup` → returns QR code
5. **2FA Verify**: `POST /api/v1/auth/totp/verify` → enables TOTP
6. Login with TOTP: include `totp_code` in the login request

## API Documentation

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs` | Swagger UI |
| `http://localhost:8000/api/redoc` | ReDoc |
| `http://localhost:8000/health` | Health check |

## Database Swap

Change `DATABASE_URL` in `backend/.env`:

```env
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./ticketsystem.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
```

## Mobile App (React Native / Expo)

The mobile app uses the same REST API. Tokens are stored via `expo-secure-store`.

```bash
just mobile-install
just mobile-start    # Expo dev server
just mobile-android  # Android emulator
just mobile-ios      # iOS simulator
```

Set the backend URL for physical devices / emulators:

```bash
EXPO_PUBLIC_API_URL=http://<your-lan-ip>:8000/api/v1 just mobile-start
```

## Code Quality

- **ruff** — Python linting + formatting
- **mypy** — Python type checking (strict)
- **ESLint 9** — TypeScript/React linting (flat config)
- **prek** — Git hooks (`just hooks-install`)
- **pytest** — Backend tests (unit + integration, SQLite in-memory)
- **Vitest 3** — Frontend component tests (jsdom)

For detailed setup and contribution instructions see [docs/developer-guide.md](docs/developer-guide.md).
