# Deployment

## Docker / Podman Compose

### Production

```bash
docker compose up -d
# or
podman-compose up -d
```

Services started:

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI (uvicorn) |
| `frontend` | 80 | nginx serving the React SPA |
| `postgres` | 5432 | PostgreSQL 18 |

### Development (hot-reload)

```bash
just dev
# or explicitly:
docker compose -f docker-compose.dev.yml up
# or with Podman:
just podman-up
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://ticketsystem:ticketsystem@localhost:5432/ticketsystem` | Full async DB URL |
| `SECRET_KEY` | — | JWT signing secret (**must** be changed in non-development environments) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `ALLOWED_ORIGINS` | `["http://localhost:3000", "http://localhost:8080"]` | CORS allowed origins |
| `UPLOAD_DIR` | `uploads` | Directory for file attachments |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max attachment size in MB |
| `TOTP_ISSUER` | `TicketSystem` | Issuer name shown in authenticator apps |
| `ENVIRONMENT` | `development` | One of `development`, `staging`, `production` |
| `DEBUG` | `false` | Enable SQLAlchemy query echo |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Database Migrations

Migrations are managed with Alembic via `just`:

```bash
# Apply all pending migrations
just backend-migrate

# Generate a new migration from SQLAlchemy model changes
just backend-migration "add column foo"

# Roll back one step
just backend-downgrade

# Reset database (drop schema → recreate → migrate)
just db-reset
```

---

## GitHub Pages

The compiled documentation lives in `docs/` at the repository root (GitHub Pages is configured to serve from that folder). The `mkdocs.yml` sets `site_dir: ../../docs` so output goes directly there.

To rebuild locally:

```bash
just docs-build
```

To preview with live-reload before committing:

```bash
just docs-serve
```

The `docs/` folder contains a `.nojekyll` file to suppress GitHub Pages' Jekyll processing.

### Automated rebuilds (CI)

The [`.github/workflows/docs.yml`](https://github.com/ticketsystem/blob/master/.github/workflows/docs.yml) workflow runs on every push to `master`. It builds the docs and commits any changes to `docs/` back to the repository automatically.
