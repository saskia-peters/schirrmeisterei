# Developer Guide

## Requirements

### System Tools

| Tool | Version | Install |
|---|---|---|
| [Python](https://www.python.org/) | ≥ 3.11 | `apt install python3.11` / [python.org](https://www.python.org/downloads/) |
| [Poetry](https://python-poetry.org/) | ≥ 1.8 | `pip install poetry` |
| [Node.js](https://nodejs.org/) | ≥ 20 LTS | [nodejs.org](https://nodejs.org/) |
| [npm](https://www.npmjs.com/) | ≥ 10 | Bundled with Node.js |
| [Docker](https://www.docker.com/) or [Podman](https://podman.io/) | ≥ 24 / ≥ 4 | [docs.docker.com](https://docs.docker.com/engine/install/) |
| [docker-compose](https://docs.docker.com/compose/) or [podman-compose](https://github.com/containers/podman-compose) | ≥ 2.x | Bundled with Docker Desktop |
| [just](https://github.com/casey/just) | ≥ 1.27 | `cargo install just` / `brew install just` / [see releases](https://github.com/casey/just/releases) |

### Optional (mobile development)

| Tool | Notes |
|---|---|
| [Expo CLI](https://expo.dev/tools) | `npm install -g expo-cli` |
| Android Studio | Required for Android emulator |
| Xcode (macOS only) | Required for iOS simulator |

---

## Project Structure

```
ticketsystem/
├── backend/          # FastAPI Python application
├── frontend/         # React TypeScript SPA
├── mobile/           # React Native (Expo) app
├── docker-compose.yml        # Production stack
├── docker-compose.dev.yml    # Development stack (hot-reload)
└── justfile          # All task shortcuts
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd ticketsystem
```

### 2. Install dependencies

```bash
just install
```

This installs both the Python backend dependencies (via Poetry) and the Node.js frontend dependencies (via npm).

To install only one side:

```bash
just backend-install    # backend only
just frontend-install   # frontend only
```

### 3. Configure environment

Copy the backend example env file and adjust as needed:

```bash
cp backend/.env.example backend/.env
```

Key variables in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-…` | **Change this** — used to sign JWT tokens |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ticketsystem.db` | Database connection string |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS origins for the API |
| `UPLOAD_DIR` | `uploads` | Directory for file attachments |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum attachment size |
| `DEBUG` | `false` | Enable debug/reload mode |

### 4. Set up pre-commit hooks (recommended)

```bash
just hooks-install
```

This installs ruff, mypy, and ESLint as Git pre-commit checks.

---

## Running the Application

### Option A — Docker / Podman (recommended)

#### Development mode (hot-reload)

Mounts the source code into the containers — changes to Python or TypeScript files are reflected immediately without rebuilding.

```bash
just dev
```

To stop:

```bash
just dev-down
```

#### Production mode

Builds optimised images and starts the full stack:

```bash
just up
```

To stop:

```bash
just down
```

#### Using Podman instead of Docker

```bash
just podman-up    # start
just podman-down  # stop
```

---

### Option B — Running locally (without Docker)

#### Backend

```bash
just backend-migrate   # apply database migrations (first time only)
just backend-run       # start the FastAPI dev server
```

The API is now available at `http://localhost:8000`.

#### Frontend

Open a second terminal:

```bash
just frontend-run
```

The React app is now available at `http://localhost:3000`.

---

## Accessing the Application

| URL | What |
|---|---|
| `http://localhost:3000` | React frontend — dev mode (local or Docker dev) |
| `http://localhost:8080` | React frontend — production Docker stack |
| `http://localhost:8000` | FastAPI backend |
| `http://localhost:8000/api/docs` | Interactive Swagger UI (API documentation) |
| `http://localhost:8000/api/redoc` | ReDoc API documentation |
| `http://localhost:8000/health` | Health check endpoint |

---

## First-time Setup

### Create the first superuser

After the backend is running, create an admin account:

```bash
just create-superuser
```

You will be prompted for an email address, full name, and password. The account is marked as `is_superuser = true`, granting access to admin-only endpoints (user management).

Alternatively, register a regular account through the web UI at `http://localhost:3000`.

---

## Database

The default database is **SQLite**, stored at `backend/ticketsystem.db`.

### Run migrations

```bash
just backend-migrate
```

### Create a new migration after changing models

```bash
just backend-migration "describe your change here"
```

### Switch to PostgreSQL

Update `DATABASE_URL` in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ticketsystem
```

Then run `just backend-migrate`. No other changes are required.

---

## Running Tests

```bash
just test              # backend + frontend
just backend-test      # backend only (pytest)
just frontend-test     # frontend only (vitest)
```

With coverage reports:

```bash
just backend-test-cov  # outputs htmlcov/index.html
just frontend-test-cov # outputs coverage/index.html
```

---

## Code Quality

```bash
just check             # all checks (lint + typecheck + tests)

# Individual checks:
just backend-lint      # ruff linter
just backend-lint-fix  # ruff linter with auto-fix
just backend-format    # ruff formatter
just backend-typecheck # mypy

just frontend-lint     # ESLint
just frontend-typecheck # tsc --noEmit
```

---

## Viewing Logs

```bash
just logs              # tail all container logs
just logs backend      # backend logs only
just logs frontend     # frontend logs only
```

---

## Mobile App (React Native / Expo)

The mobile app shares the same backend API.

```bash
just mobile-install    # install dependencies
just mobile-start      # start Expo dev server

just mobile-android    # run on Android emulator
just mobile-ios        # run on iOS simulator (macOS only)
```

Set the backend URL via the `EXPO_PUBLIC_API_URL` environment variable before starting:

```bash
EXPO_PUBLIC_API_URL=http://<your-machine-ip>:8000/api/v1 just mobile-start
```

> **Note:** Use your LAN IP (e.g. `192.168.1.x`), not `localhost`, when connecting a physical device or emulator to the backend running on your machine.

---

## All Available Commands

Run `just` (no arguments) to list every available command:

```
just
```

Or see the [justfile](../justfile) directly.
