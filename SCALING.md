# Scaling Guide

> **Document purpose:** practical, step-by-step instructions for growing the ticketsystem
> from its current 20–30-user baseline to progressively larger deployments.
>
> For the full findings list and architectural rationale see [REVIEW.md](REVIEW.md).
> Code comments tagged `SCALE-UP` in the source point directly to the spots that need
> to change when a tier boundary is crossed.

---

## Current Deployment Profile

| Property | Current value |
|----------|--------------|
| Target users | 20–30 concurrent |
| Backend replicas | 1 (single process) |
| Database | 1 PostgreSQL instance (Docker volume) |
| File storage | Local disk (`uploads/` volume) |
| Cache / message broker | None |
| Rate limiting | `slowapi` in-memory per-process — switch to Redis at Tier-3 (S-5 ✅) |
| Deployment | `docker-compose.yml` on a single host |

This profile is appropriate for the **pilot phase**.  The application has been deliberately
kept simple: no Redis, no PgBouncer, no object-storage dependency.  Infrastructure
complexity must earn its place; at 20–30 users it would not.

---

## Growth Triggers and Actions

The table below maps observable symptoms to the actions that resolve them.
Work top-to-bottom; each tier assumes the previous one is complete.

| Tier | When to act | Trigger signal | Actions |
|------|------------|---------------|---------|
| **0 — Security** | ✅ All Tier-0 items resolved | — | All S-1 … S-9 fixed; see REVIEW.md for details |
| **1 — 30–50 users** | Pilot feedback period | Occasional slow page loads (P95 > 1 s) | Pool tuning, pagination, chunked uploads |
| **2 — 50–100 users** | Early production growth | DB connection errors in logs | Readiness endpoint, structured logging, migrate `/health` |
| **3 — 100–300 users** | Sustained production use | Multi-replica needed OR rate-limit gaps exposed | Redis (rate limit + JTI + org cache), refresh-token revocation |
| **4 — 300–500 users** | High-growth phase | Attachment throughput is a bottleneck | Object storage (MinIO / S3) |
| **5 — 500+ users** | Enterprise scale | DB is the bottleneck | PgBouncer + managed HA PostgreSQL, CDN, read replicas |

---

## Tier 0 — Security (Do Now, Scale-Independent)

These are security vulnerabilities that exist at any user count.
See REVIEW.md Tier-0 table for the full list.  Priority order:

1. ~~**S-2** — Comment update/delete don't enforce `ticket_id`~~ ✅ Fixed v1.8
2. ~~**S-3** — TOTP replay within 30-second window~~ ✅ Fixed v1.9
3. ~~**S-4** — No refresh token revocation (TOTP bypass via stolen token)~~ ✅ Fixed v2.0
4. ~~**S-5** — No rate limiting on login/TOTP/reset endpoints~~ ✅ Fixed v2.1
5. ~~**S-6** — SMTP password in plaintext in DB~~ ✅ Fixed v2.2
6. ~~**S-7** — Refresh token in `localStorage` (XSS risk)~~ ✅ Fixed v2.3
   - `/auth/login` + `/auth/refresh`: set `HttpOnly; Secure; SameSite=Strict` cookie; body returns only `access_token`
   - `/auth/logout`: clears the cookie on the server
   - `COOKIE_SECURE=false` in dev (HTTP); must be `true` in production
   - `refreshToken` removed from Zustand store and `localStorage` persistence
7. ~~**S-8** — Concurrent token refresh race condition~~ ✅ Fixed v2.4
   - `refreshPromise` module-level singleton in `client.ts`; concurrent 401s all await the same promise
   - Promise cleared in `.finally()` so subsequent genuine token expiries start a fresh refresh
8. ~~**S-9** — `ALLOWED_ORIGINS` hardcoded to `localhost` in production compose~~ ✅ Fixed v2.5
   - `allow_methods` restricted to `["GET","POST","PATCH","DELETE","OPTIONS"]`; `allow_headers` to `["Authorization","Content-Type"]`
   - `ALLOWED_ORIGINS` env var required (no default) in `docker-compose.yml` + `deploy/docker-compose.yml`
   - `config.py` startup validator rejects localhost/wildcard origins in `ENVIRONMENT=production`

---

## Tier 1 — 30–50 Users

### 1.1 Database Connection Pool

**File:** `backend/app/db/session.py`
**Config:** `backend/app/core/config.py` and `.env` / compose environment

The pool settings are already env-configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
No code change is needed — just update the environment:

```env
# .env or docker-compose.yml environment section
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true
```

| Phase | `pool_size` | `max_overflow` | Notes |
|-------|------------|---------------|-------|
| ≤30 users (current) | 5 | 10 | Docker default |
| 30–50 users | 10 | 20 | Single replica, moderate load |
| 50–100 users (single replica) | 20 | 30 | Monitor `pool_timeout` errors |
| 100+ users with PgBouncer | 5 | 10 per replica | PgBouncer multiplexes at the DB layer |

> **Note:** PostgreSQL's default `max_connections = 100`.  Never set
> `pool_size + max_overflow` above ~80 without also deploying PgBouncer
> (Tier 5) or increasing `max_connections` in `postgresql.conf`.

### 1.2 Pagination

**Files:** `backend/app/api/v1/endpoints/tickets.py`, `backend/app/services/ticket_service.py`
**REVIEW.md:** P-1

Add `skip` / `limit` query parameters to list and board endpoints.  Without pagination
a single request fetches every ticket in the system — this becomes a denial-of-service
vector as ticket volume grows.

```python
# tickets.py — list endpoint
@router.get("/", response_model=list[TicketSummary])
async def list_tickets(
    status: TicketStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    ...
)
```

```python
# ticket_service.py — add to list_all / list_by_status
stmt = stmt.offset(skip).limit(limit)
```

### 1.3 Upload Chunking

**File:** `backend/app/services/ticket_service.py` (see `SCALE-UP (P-4)` comment)
**File:** `frontend/nginx.conf` (see `SCALE-UP` comment — uncomment `client_max_body_size`)

Currently the entire file is read into memory before the size check.  When
`MAX_UPLOAD_SIZE_MB` is raised or request concurrency increases, replace
`await file.read()` with the chunked pattern shown in the code comment:

```python
buf = b""
async for chunk in file:
    buf += chunk
    if len(buf) > max_size:
        raise ValidationException(f"File too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB")
contents = buf
```

At the same time, uncomment `client_max_body_size 11M;` in `nginx.conf` so nginx
does not reject the request before it reaches the backend.

---

## Tier 2 — 50–100 Users

### 2.1 Health and Readiness Endpoints

**File:** `backend/app/main.py`
**REVIEW.md:** H-5

Split the single `/health` endpoint into two:

```python
@app.get("/health")   # liveness — always returns 200 if the process is running
async def liveness() -> dict:
    return {"status": "ok"}

@app.get("/readiness")  # readiness — returns 503 if DB is unreachable
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
```

Update `docker-compose.yml` healthcheck to use `/readiness`.  Orchestrators
(Docker Swarm, Kubernetes) use this to stop routing traffic to unhealthy replicas.

### 2.2 Structured Logging

**File:** `backend/app/main.py` (middleware) + individual service/endpoint files
**REVIEW.md:** O-1

Install `structlog` + `asgi-correlation-id`:

```
uv add structlog asgi-correlation-id
```

Add middleware in `main.py`:

```python
from asgi_correlation_id import CorrelationIdMiddleware
app.add_middleware(CorrelationIdMiddleware)
```

Log key security events:
- `login.success` / `login.failure`
- `token.refresh`
- `permission.denied`
- `totp.fail`
- `attachment.upload`
- `ticket.status_change`

This is also required for meaningful incident analysis if a security event is reported.

### 2.3 CORS Hardening ✅ Fixed v2.5

~~**File:** `backend/app/main.py` (see `SCALE-UP (S-9)` comment)~~
~~**REVIEW.md:** S-9~~

**Done:** `allow_methods` and `allow_headers` are now explicit allowlists; `ALLOWED_ORIGINS` is required
in production (no localhost default); `config.py` validator rejects unsafe origins at startup.

---

## Tier 3 — 100–300 Users

### 3.1 Add Redis

**Files:** `docker-compose.yml`, `backend/pyproject.toml`

Redis becomes the shared backing store for rate limiting, refresh-token JTI,
and (optionally) org-hierarchy caching.

```yaml
# docker-compose.yml — add service:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis-data:
```

```
uv add redis[hiredis] slowapi
```

Add to `config.py`:

```python
REDIS_URL: str = "redis://redis:6379/0"
```

### 3.2 Rate Limiting ✅ Implemented (S-5 v2.1)

**REVIEW.md:** ~~S-5~~ ✅ Fixed
**Files:** `backend/app/core/limiter.py`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/api/v1/endpoints/auth.py`

`slowapi` is active with an **in-memory** backing store (`RATE_LIMIT_STORAGE_URI=memory://`).
Limits applied:

| Endpoint | Limit |
|---|---|
| `POST /auth/login` | 10 / minute per IP |
| `POST /auth/totp/verify` | 10 / minute per IP |
| `DELETE /auth/totp/disable` | 10 / minute per IP |
| `POST /auth/password-reset/request` | 5 / minute per IP |

**Upgrade path:** Set `RATE_LIMIT_STORAGE_URI=redis://redis:6379/1` at Tier-3 (100+ users /
multi-replica) to share counters across all backend processes.  Zero code change required.

### 3.3 Refresh Token Revocation (JTI Store) ✅ Implemented (S-4 v2.0)

**REVIEW.md:** ~~S-4~~ ✅ Fixed
**Files:** `backend/app/core/security.py`, `backend/app/api/v1/endpoints/auth.py`, `backend/app/models/models.py`, `backend/alembic/versions/0004_add_refresh_tokens_table.py`

A `refresh_tokens` table now tracks every issued JTI with `user_id` and `expires_at`.
`POST /auth/refresh` validates the JTI before rotating, `POST /auth/logout` revokes all
tokens for the user, and TOTP enable/disable also revoke all existing sessions.

At Tier-3 scale (300+ users), migrate the JTI store from PostgreSQL to **Redis** with
`SETEX jti:<jti> <ttl_seconds> 1` for O(1) lookups and automatic expiry.

<!-- original implementation note preserved below -->
<!--

```sql
-- Alembic migration
CREATE TABLE ticketsystem.refresh_tokens (
    jti       UUID PRIMARY KEY,
    user_id   VARCHAR(36) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
```

On `/auth/refresh`: verify JTI exists in store, then rotate (delete old, insert new).
On logout / TOTP enable: delete all JTIs for the user.
-->

### 3.4 Organisation Hierarchy Cache

**File:** `backend/app/services/organization_service.py` (see `SCALE-UP (P-2)` comment)
**REVIEW.md:** P-5

Cache `get_visible_org_ids(org_id)` in Redis with a 5-minute TTL.
Invalidate on any org create / update / delete.  This eliminates the BFS
multi-query pattern from every list/board request:

```python
CACHE_TTL = 300  # 5 minutes

async def get_visible_org_ids(self, user_org_id: str | None) -> list[str] | None:
    cache_key = f"org_visible:{user_org_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    result = await self._compute_visible_org_ids(user_org_id)
    await redis.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result
```

At the same time, replace the BFS `get_descendants` with a PostgreSQL recursive CTE
(single round-trip):

```sql
WITH RECURSIVE tree AS (
    SELECT id FROM ticketsystem.organizations WHERE id = :root_id
    UNION ALL
    SELECT o.id FROM ticketsystem.organizations o
    JOIN tree t ON o.parent_id = t.id
)
SELECT id FROM tree;
```

---

## Tier 4 — 300–500 Users

### 4.1 Object Storage for Attachments

**REVIEW.md:** H-1
**Files:** `backend/app/services/ticket_service.py`, `backend/app/api/v1/endpoints/tickets.py`

Local disk attachments **cannot be shared across multiple backend replicas**.
Migrate to MinIO (self-hosted) or AWS S3 / Google Cloud Storage.

**Deployment (MinIO):**

```yaml
# docker-compose.yml
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-ticketsystem}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:-changeme}
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
```

**Config additions:**

```python
# config.py
STORAGE_BACKEND: Literal["local", "s3"] = "local"
S3_ENDPOINT_URL: str | None = None          # e.g. "http://minio:9000"
S3_BUCKET_NAME: str = "ticketsystem"
S3_ACCESS_KEY: str = ""
S3_SECRET_KEY: str = ""
```

**Service changes:**

```python
# ticket_service.py — replace aiofiles.open() block with:
if settings.STORAGE_BACKEND == "s3":
    await s3_client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=s3_key,
        Body=contents,
        ContentType=detected_mime,
    )
    file_path = s3_key   # store the S3 key, not a local path
else:
    # existing local-disk code
    ...
```

**Endpoint changes:**

```python
# tickets.py — download_attachment:
if settings.STORAGE_BACKEND == "s3":
    url = await s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": attachment.file_path},
        ExpiresIn=300,
    )
    return RedirectResponse(url)
else:
    # existing FileResponse code
    ...
```

---

## Tier 5 — 500+ Users

### 5.1 Multiple Backend Replicas

**Prerequisite:** Object storage (Tier 4) must be complete — local disk attachments
are not shared across processes.

```yaml
# docker-compose.yml (Docker Swarm mode) or Kubernetes Deployment
deploy:
  replicas: 3
  update_config:
    parallelism: 1
    delay: 10s
```

Ensure `SESSION_TYPE` / token storage is Redis-backed before running replicas.

### 5.2 PgBouncer

**REVIEW.md:** H-6

```yaml
  pgbouncer:
    image: bitnami/pgbouncer:latest
    environment:
      POSTGRESQL_HOST: postgres
      POSTGRESQL_PORT: 5432
      PGBOUNCER_DATABASE: ticketsystem
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_MAX_CLIENT_CONN: 500
      PGBOUNCER_DEFAULT_POOL_SIZE: 20
```

Update `DATABASE_URL` to point at `pgbouncer:5432` instead of `postgres:5432`.

Set `DB_POOL_SIZE=5, DB_MAX_OVERFLOW=10` per replica; PgBouncer handles the fan-in.

### 5.3 Managed HA PostgreSQL

**REVIEW.md:** H-3

Options (in order of operational effort):

| Option | When to use |
|--------|------------|
| **Supabase** (managed) | Easiest migration; same Postgres wire protocol |
| **AWS RDS Multi-AZ** | AWS-centric deployments |
| **Google Cloud SQL HA** | GCP deployments |
| **Patroni + HAProxy** | Self-hosted, air-gapped environments |

Add `DATABASE_READ_URL` to config for read-replica routing of list endpoints.

### 5.4 Native UUID Primary Keys

**REVIEW.md:** P-6

PKs are currently stored as `VARCHAR(36)` text UUIDs (`String(36)` in SQLAlchemy).
Migrating to PostgreSQL's native `UUID` type saves 20 bytes per row, improves
B-tree index performance and enables in-DB UUID generation.

This is a pure Alembic migration — no application code changes are required because
SQLAlchemy's `UUID` type maps to the same Python `str` in recent versions.

```python
# Alembic migration
op.alter_column("tickets", "id", type_=postgresql.UUID(as_uuid=False))
# repeat for all PK/FK columns
```

**Schedule this during a planned maintenance window** before traffic spikes, when
the migration cost (table rewrite) is lowest.

---

## Configuration Reference

All tuneable values live in `backend/app/core/config.py` and can be set via
environment variables or `.env` file.  The table shows the full scaling-relevant set:

| Env var | Default | Change at |
|---------|---------|-----------|
| `DB_POOL_SIZE` | `5` | 30+ users — see Tier 1 |
| `DB_MAX_OVERFLOW` | `10` | 30+ users — see Tier 1 |
| `DB_POOL_RECYCLE` | `1800` | Leave as-is unless seeing stale connection errors |
| `DB_POOL_PRE_PING` | `true` | Leave as-is |
| `MAX_UPLOAD_SIZE_MB` | `10` | When users need larger files; also update nginx |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No change needed |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Can reduce to `1` now that JTI rotation is active (S-4 ✅) |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | Must be set to real domain in production |
| `REDIS_URL` | *(add in Tier 3)* | `redis://redis:6379/0` |
| `STORAGE_BACKEND` | `local` | `s3` in Tier 4 |
| `S3_ENDPOINT_URL` | *(add in Tier 4)* | MinIO or cloud endpoint |

---

## Code Comment Index

All `SCALE-UP` comments in the codebase:

| File | Comment tag | Action |
|------|------------|--------|
| `backend/app/services/ticket_service.py` | `SCALE-UP (P-4)` | Chunked file upload reads |
| `backend/app/services/ticket_service.py` | `SCALE-UP (P-3)` | Split eager-load into summary/detail options |
| `backend/app/services/organization_service.py` | `SCALE-UP (P-2)` | Replace BFS with recursive CTE |
| ~~`backend/app/main.py`~~ | ~~`SCALE-UP (S-9)`~~ | ~~Restrict `allow_methods`~~ ✅ Fixed v2.5 |
| `frontend/nginx.conf` | `SCALE-UP (P-4)` | Uncomment `client_max_body_size` |

---

## Quick Checklist: Before Go-Live (Any Scale)

- [x] `SECRET_KEY` changed from default (enforced at startup in non-dev `ENVIRONMENT`)
- [x] `ALLOWED_ORIGINS` set to actual domain(s), no `localhost` (enforced at startup) ✅ S-9 v2.5
- [x] `ENVIRONMENT=production` in compose (enables the `SECRET_KEY` + `ALLOWED_ORIGINS` validators)
- [ ] `POSTGRES_PASSWORD` changed from default
- [x] Tier-0 security item S-7 resolved (refresh token → HttpOnly cookie) ✅ v2.3
- [x] Tier-0 security item S-8 resolved (concurrent refresh race condition) ✅ v2.4
- [x] Tier-0 security item S-9 resolved (CORS hardening) ✅ v2.5
- [ ] `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` reviewed against expected concurrency
- [ ] Backups configured for the `postgres-data` Docker volume
- [ ] Uploaded attachments volume (`backend-uploads`) included in backup scope
