# Architecture Review

!!! info "Living Document"
    This document is updated periodically as the system evolves. Each review is stamped with a date and a status tier. Use the [Progress Tracker](#progress-tracker) section to follow how architectural gaps are being resolved over time.

---

## Review History

| Date | Reviewer | Status | Summary |
|------|----------|--------|---------|
| 2026-04-06 | Initial review | 🟡 Maturing | First full architecture review; baseline established || 2026-04-13 | Security hardening pass | 🟢 Healthy | S-7/S-8/S-9 fixes applied; email ingestion added; IMAP security review completed |
---

## 1. System Overview

TicketSystem is a **multi-tenant support-ticket platform** built for hierarchical German emergency/volunteer organisations (DRK structure: Ortsverband → Regionalstelle → Landesverband → Leitung).

### Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Frontend | React + Vite + TypeScript | React 18.3, TS 5.5 | SPA, REST-only |
| Mobile | Expo / React Native | Expo 51, RN 0.74 | Early scaffold |
| Backend | FastAPI + uvicorn | Python 3.13 | Async throughout |
| ORM | SQLAlchemy (async) | ≥2.0 | Alembic migrations |
| Database | PostgreSQL | 18 | Schema: `ticketsystem` |
| Auth | JWT HS256 + bcrypt + TOTP | PyJWT ≥2.8, pyotp | Dual-token |
| Container | Podman Compose | — | Dev + prod profiles |
| CI/CD | GitHub Actions | — | Test + build + docs |
| Docs | MkDocs Material | mkdocs 1.6 | Published to `docs/` |

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  Clients                                                         │
│                                                                  │
│  ┌──────────────────────┐   ┌────────────────────────────────┐  │
│  │  React SPA           │   │  Expo / React Native           │  │
│  │  Vite · TypeScript   │   │  (mobile scaffold)             │  │
│  │  React Query         │   │  SecureStore token storage     │  │
│  │  Zustand (auth)      │   │                                │  │
│  │  dnd-kit (Kanban)    │   │                                │  │
│  └──────────┬───────────┘   └───────────────┬────────────────┘  │
└─────────────┼───────────────────────────────┼────────────────────┘
              │ HTTPS / REST (JSON)            │ HTTPS / REST
              ▼                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI Backend  (Python 3.13 · uvicorn ASGI)                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │  /auth   │  │ /tickets │  │  /users  │  │    /admin     │   │
│  │          │  │          │  │          │  │               │   │
│  │ JWT auth │  │ CRUD     │  │ profile  │  │ config items  │   │
│  │ TOTP 2FA │  │ status   │  │ avatar   │  │ org hierarchy │   │
│  │ refresh  │  │ Kanban   │  │ groups   │  │ bulk upload   │   │
│  │ HttpOnly │  │ attach.  │  │          │  │ permissions   │   │
│  │ cookie   │  │ PDF+img  │  │          │  │ email ingest  │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Services layer                                          │   │
│  │  UserService · TicketService · OrganizationService       │   │
│  │  TotpService · EmailIngestionService · ImapPoller        │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │ asyncpg                               │
└─────────────────────────┼──────────────────────────────────────-┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  PostgreSQL 18   (schema: ticketsystem)                          │
│                                                                  │
│  organisations · users · tickets · attachments · comments        │
│  status_logs · user_groups · permissions · role_permissions      │
│  config_items · app_settings · email_configs                     │
└──────────────────────────────────────────────────────────────────┘
          │                   │
    named volume     ┌─────────────────────────────┐
    (uploads dir.)   │  External mail server (IMAP) │
    attachments +    │  SSL/TLS · port 993           │
    avatars          │  polled by ImapPoller (async) │
                     └─────────────────────────────┘
```

---

## 3. Organisation Hierarchy & Multi-Tenancy

### Hierarchy

```
Leitung (LTG)
  └── Landesverband (LV)
        └── Regionalstelle (Rst)
              └── Ortsverband (OV)
```

Every user belongs to exactly one organisation node. Visibility is enforced server-side by `OrganizationService.get_visible_org_ids()`:

| Org Level | Visible Scope |
|-----------|---------------|
| Leitung | Entire system (all tickets) |
| Landesverband | Own LV subtree |
| Regionalstelle | Own Rst subtree |
| Ortsverband | Own OV only |

### Implementation Notes

- Subtree traversal uses BFS (`get_descendants`).
- Superusers bypass all org-scoping (returns `None` → no filter applied).
- Org hierarchy can be seeded in bulk via `POST /admin/hierarchy/upload` (XLSX).

---

## 4. Data Model

### Entity Relationship Overview

```
organizations ─────────────────────────────────────────────────┐
  id, name, level, parent_id (self-ref)                        │
       │                                                        │
       ├──► users                                              │
       │      id, email, hashed_password, full_name            │
       │      is_superuser, force_password_change               │
       │      totp_enabled, totp_secret, avatar_url            │
       │      organization_id ──────────────────────────────────┘
       │         │
       │         ├──► user_group_memberships ──► user_groups
       │         │                                  id, name
       │         │                                  └──► role_permissions ──► permissions
       │         │
       │         ├──► tickets (as creator / owner)
       │         │      id, title, description, status
       │         │      creator_id, owner_id, organization_id
       │         │      priority_id, category_id, affected_group_id (→ config_items)
       │         │      waiting_for
       │         │        ├──► attachments
       │         │        ├──► comments (with author_id)
       │         │        └──► status_logs (change history)
       │         │
       │         └──► comments, status_logs
       │
       └──► email_configs (one per org)

config_items: { priority | category | group } — soft-deleted via is_active
app_settings: key→value store for age thresholds and other tunables
```

### Key Design Decisions

- All PKs are UUID strings (not auto-increment integers) — good for distributed import/merge.
- Timestamps are timezone-aware (`DateTime(timezone=True)`) throughout.
- Cascade deletes on `attachments`, `comments`, `status_logs` from `tickets`.
- `UserGroupMembership.helfende` is always enforced — users always have at least the `helfende` role.
- Soft deletion not used for tickets or users — hard delete with FK constraints enforced by Postgres.

---

## 5. Authentication & Authorisation

### Authentication Flow

```
Client                          Backend
  │                               │
  ├─ POST /auth/login ────────────►│  validate email + bcrypt password
  │  { email, password, [totp] }  │  [if totp_enabled] verify TOTP code
  │                               │
  │◄─ { access_token (30m),       │  sign JWT HS256 with sub=user_id
  │      refresh_token (7d) } ────┤  type="access" / type="refresh"
  │                               │
  ├─ API calls with Bearer ───────►│  decode JWT → load user → check active
  │                               │
  ├─ POST /auth/refresh ──────────►│  validate refresh token, issue new pair
  │◄─ { new access_token } ───────┤
```

Frontend handles token refresh transparently via Axios interceptor (retry on 401).

### TOTP / 2FA Setup Flow

```
1. POST /auth/totp/setup   → returns { secret, qr_code_base64 }
2. User scans QR in authenticator app
3. POST /auth/totp/verify  → { code } — enables TOTP on success
4. DELETE /auth/totp/disable → { code } — disables TOTP
```

### Authorisation (RBAC)

Three built-in roles with permission sets:

| Role | Key Permissions |
|------|----------------|
| `helfende` | `view_ticket`, `create_ticket`, `comment_ticket` |
| `schirrmeister` | + `assign_ticket`, `close_ticket`, `edit_ticket`, `manage_ticket` |
| `admin` | All of the above + `manage_users`, `manage_config`, … |

- Permissions are stored in the `permissions` table and linked to `user_groups` via `role_permissions`.
- `UserService.user_has_permission(user, codename)` checks group membership → permission.
- The `force_password_change` flag gates all non-profile endpoints until the password is changed.

---

## 6. API Design

### Structure

All endpoints live under `/api/v1/`. There are five routers:

| Router | Prefix | Auth Level |
|--------|--------|------------|
| `auth` | `/auth` | Mixed (public + Bearer) |
| `tickets` | `/tickets` | Bearer |
| `users` | `/users` | Bearer (mixed superuser) |
| `admin` | `/admin` | Bearer (admin group / superuser) |
| `organizations` | `/organizations` | Public |

### Design Observations

- Consistent use of Pydantic v2 schemas for request/response validation.
- HTTP method semantics: `PATCH` for partial updates, `PUT` for full replacement (group permissions).
- Custom exception classes map cleanly to HTTP status codes.
- File uploads use `multipart/form-data`; files stored on disk under `UPLOAD_DIR` with UUID names to prevent path traversal.
- No API versioning beyond the `/v1` prefix — no `v2` yet.
- `GET /health` endpoint available for load-balancer probes.
- OpenAPI docs available at `/api/docs` (Swagger) and `/api/redoc`.

---

## 7. Frontend Architecture

### State Management

| Concern | Tool | Notes |
|---------|------|-------|
| Auth state (tokens, user) | Zustand (persisted) | `localStorage`; re-hydrated on page load |
| Server state (tickets, board, users) | TanStack Query v5 | Caching, background refresh (30 s for board) |
| Form state | react-hook-form + zod | Schema-validated forms |
| UI interaction (drag-drop) | @dnd-kit | Kanban board column transitions |

### Routing

React Router v6 with three tiers:
1. **Unauthenticated**: Login / Register (state-switched, no URL)
2. **Force password change**: Blocking modal covers all routes
3. **Authenticated**: `/` (Board), `/admin` (Admin Panel), `/profile` (Profile)

### Key Patterns

- All API calls are centralised in `api/index.ts`; TanStack Query hooks wrap them in `hooks/useApi.ts`.
- The Axios client auto-attaches `Authorization: Bearer` header from the Zustand store.
- The frontend is a pure SPA — no SSR; nginx serves it in production.
- The Navbar background colour reflects the user's organisation level (visual context indicator).

---

## 8. Mobile App

The mobile app (`mobile/`) is a **scaffold** built on Expo 51 / React Native 0.74.

### Current State

| Feature | Status |
|---------|--------|
| Auth (login + JWT) | ✅ Implemented |
| `GET /auth/me` | ✅ Implemented |
| Ticket list (board view) | ✅ Implemented |
| Token storage | ✅ SecureStore |
| Navigation | ⬜ Empty scaffold |
| Ticket detail | ⬜ Not started |
| Create/edit ticket | ⬜ Not started |
| TOTP support | ⬜ Not started |
| Push notifications | ⬜ Not started |
| Offline support | ⬜ Not started |

The mobile app shares the same REST API — no separate mobile-specific endpoints exist.

---

## 9. Testing

### Backend

| Scope | Runner | Count (approx.) | Coverage |
|-------|--------|------------------|----------|
| Unit | pytest | ~30 tests | Security, TOTP, UserService, OrganizationService |
| Integration | pytest + httpx | ~36 tests | Auth flows, ticket CRUD, status transitions |
| Total | — | ~66 tests | HTML coverage report in `htmlcov/` |

Test database: in-memory SQLite with `aiosqlite` — no Postgres required for tests.
Key fixture: `conftest.py` seeds `helfende`/`schirrmeister`/`admin` groups and core permissions.

### Frontend

Component tests with Vitest + Testing Library in `components/**/__tests__/`.

### Gaps

- No end-to-end (E2E) tests (Playwright / Cypress).
- No load / performance tests.
- Frontend test coverage is not measured or enforced.
- Mobile has no tests at all.

---

## 10. CI/CD Pipeline

```
push to master
       │
       ├─► backend-test job
       │     ruff lint → ruff format check → mypy → pytest --cov
       │
       ├─► frontend-test job
       │     eslint → tsc --noEmit → vitest --coverage
       │
       └─► docker-build job  (needs both test jobs)
             docker build backend
             docker build frontend

push to master/main
       └─► docs.yml job
             mkdocs build → git commit docs/ → push [skip ci]
```

### Observations

- No deploy step — build artefacts are not pushed to a registry or deployed automatically.
- Docker images are only built, not tagged or published.
- `docs/` is auto-committed by the workflow — this creates mixed commits in `master`.
- Coverage reports are uploaded to Codecov.

---

## 11. Deployment

### Production Stack (Podman Compose)

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| `postgres` | `postgres:18` | internal | named volume `postgres-data` |
| `backend` | local build | `8000` | named volume `backend-uploads` |
| `frontend` | local build (nginx) | `8080:80` | static SPA |

No TLS termination is configured in the compose stack — expected to be behind a reverse proxy (nginx / Caddy / Traefik) in production.

### Environment Variables (critical)

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | Yes | Validated non-default in non-dev environments |
| `DATABASE_URL` | Yes | Async postgres DSN |
| `ALLOWED_ORIGINS` | Yes | CORS whitelist |
| `UPLOAD_DIR` | Yes | Filesystem path for attachments |

---

## 12. Security Assessment

### Strengths

- **Passwords**: bcrypt with salt, never stored or logged in plain.
- **JWT**: Short-lived access tokens (30 min); **refresh token stored in HttpOnly cookie** — not accessible to JavaScript.
- **Axios refresh queue**: concurrent 401 responses serialised behind a single in-flight refresh call.
- **Path traversal prevention**: Attachments and avatars stored under UUID filenames via `get_safe_upload_path`.
- **MIME validation**: Attachment uploads validate content type against magic bytes (not client-supplied header).
- **PDF support**: PDF attachments validated via `%PDF` magic bytes; allowed in ticket creation and email ingestion.
- **TOTP 2FA**: Optional per-user, QR code provisioned securely.
- **Org scoping**: Server-side enforcement; clients cannot escalate visibility.
- **Email ingestion org-scope**: Non-superuser senders may only comment on tickets in their own organisation.
- **Permission checks**: Centralised in `UserService.user_has_permission`.
- **Force password change**: Blocks all endpoints until resolved.
- **Schema isolation**: All tables in `ticketsystem` Postgres schema.
- **SMTP credentials encrypted**: Fernet-encrypted at rest using a key derived from `SECRET_KEY`.
- **CORS origin validation**: Startup validator rejects wildcard or localhost-only origins in production.
- **IMAP security**: Connection timeout (30 s), message size cap (10 MB), MIME-part count limit (50), filename length cap (255 chars), bracket-only subject pattern, `_mark_seen` decoupled from DB transaction, SSL enforced in production.

### Weaknesses / Gaps

!!! warning "Open Security Items"

    | # | Issue | Severity | Status |
    |---|-------|----------|--------|
    | S-1 | Refresh tokens are not revocable (no token blacklist / rotation) | Medium | � Partial — HttpOnly cookie closes XSS exfil; server-side revocation still open |
    | S-2 | No rate limiting on login / password reset endpoints | Medium | 🔴 Open |
    | S-3 | `SECRET_KEY` placeholder check raises hard `ValueError` at startup in non-dev environments | Low | ✅ Closed |
    | S-4 | SMTP passwords stored in plain text in `email_configs` table | Medium | ✅ Closed — Fernet-encrypted at rest |
    | S-5 | No HTTPS enforcement or HSTS header in compose stack (relies on upstream proxy) | Low | 🟡 Open |
    | S-6 | File size limits enforced in code but not at the nginx/proxy layer | Low | 🟡 Open |
    | S-7 | Admin bulk upload XLSX: no row-count cap (DoS potential for very large files) | Low | 🟡 Open |
    | S-8 | CORS origins not validated at startup in production | Medium | ✅ Closed — startup `model_validator` rejects wildcard/localhost in production |

---

## 13. Technical Debt & Known Gaps

!!! note "Tracking"
    Items below are tracked as architectural gaps. Mark them resolved when addressed and record the date.

### Backend

| # | Item | Priority | Status | Resolved |
|---|------|----------|--------|----------|
| B-1 | No background task queue (Celery / ARQ) — email sending would block the request | Medium | � Mitigated — IMAP ingestion uses asyncio task + run_in_executor | — |
| B-2 | Email notifications not implemented (SMTP config exists but emails are never sent) | High | 🔴 Open | — |
| B-3 | Email ingestion (IMAP poller) not implemented | High | ✅ Closed | 2026-04-13 |
| B-3 | No soft-delete for tickets or users | Low | 🟡 Open | — |
| B-3 | Email ingestion (IMAP poller) not implemented | High | ✅ Closed | 2026-04-13 |
| B-3 | Email ingestion (IMAP poller) not implemented | High | ✅ Closed | 2026-04-13 |
| B-4 | `organization_service.py` not in services layer (only added in migration; isolated) | Low | 🟡 Open | — |
| B-5 | Single Alembic migration chain — merge conflicts painful for parallel branches | Low | 🟡 Open | — |
| B-6 | `app_settings` only seeded via `GET /admin/app-settings` side-effect — fragile init path | Low | 🟡 Open | — |
| B-7 | `helfende` group always added on `assign_groups` call — undocumented business rule | Low | 🟡 Open | — |
| B-8 | Avatar file orphan risk: deleting user does not delete avatar file from disk | Low | 🟡 Open | — |

### Frontend

| # | Item | Priority | Status | Resolved |
|---|------|----------|--------|----------|
| F-1 | No error boundary — unhandled React errors crash the full page | Medium | 🔴 Open | — |
| F-2 | Auth state in `localStorage` — vulnerable to XSS if tokens stored as plain strings | Medium | 🔴 Open | — |
| F-3 | Board auto-refresh is polling (30 s) — no WebSocket / SSE for real-time updates | Low | 🟡 Open | — |
| F-4 | No pagination on ticket list / board — performance degrades with large ticket counts | Medium | 🔴 Open | — |
| F-5 | React Router uses state-switch for login/register (no browser back-button support) | Low | 🟡 Open | — |
| F-6 | No toast/feedback for all async operations (some errors silently fail) | Low | 🟡 Open | — |
| F-7 | `frontend-test` target not in justfile (only indirectly via CI) | Low | 🟡 Open | — |

### Mobile

| # | Item | Priority | Status | Resolved |
|---|------|----------|--------|----------|
| M-1 | App is a scaffold — navigation, detail views, create/edit not implemented | High | 🔴 Open | — |
| M-2 | No tests | Medium | 🔴 Open | — |
| M-3 | No TOTP support in login screen | Medium | 🔴 Open | — |
| M-4 | No push notifications | Low | 🟡 Open | — |
| M-5 | `docker-compose.dev.yml` does not include mobile/Expo service | Low | 🟡 Open | — |

### Infrastructure / DevOps

| # | Item | Priority | Status | Resolved |
|---|------|----------|--------|----------|
| I-1 | No container registry push in CI — images built but not published | Medium | 🔴 Open | — |
| I-2 | No automatic deploy step in CI/CD | Medium | 🔴 Open | — |
| I-3 | `docs/` committed to master — pollutes git history | Low | 🟡 Open | — |
| I-4 | No staging environment | Medium | 🔴 Open | — |
| I-5 | No database backup/restore strategy documented | Medium | 🔴 Open | — |
| I-6 | `docker-compose.dev.yml` frontend service uses `npm` not `pnpm` | Low | 🟡 Open | — |

---

## 14. Progress Tracker

This section is updated with each review to record what has been resolved since the last entry.

### 2026-04-06 — Baseline (v0.1)

**Completed features at this point:**

- ✅ Full RBAC permission system (helfende / schirrmeister / admin)
- ✅ Multi-tenant org hierarchy (4-level, XLSX import)
- ✅ Kanban board with drag-and-drop
- ✅ Ticket lifecycle (create → working → waiting → resolved → closed)
- ✅ Status log history
- ✅ Attachments (image upload, per-ticket)
- ✅ Comments (threaded, author-editable)
- ✅ TOTP 2FA (setup, enable, disable)
- ✅ Avatar upload and management
- ✅ Bulk user import (XLSX)
- ✅ Per-org SMTP email config (stored, UI present — sending not yet implemented)
- ✅ Age threshold colouring (green → dark red, configurable)
- ✅ Force password change flow
- ✅ Admin panel (config items, groups, permissions, settings, email, bulk ops)
- ✅ CI pipeline (lint + typecheck + test + docker build)
- ✅ MkDocs documentation site
- ✅ 66 backend tests passing

**Open work at this point:**

- ⏳ Email sending (SMTP wired, not triggered — B-2)
- ⏳ Mobile app (scaffold only — M-1)
- ⏳ E2E tests
- ⏳ Container registry + deploy step (I-1, I-2)

---

### 2026-04-13 — Security Hardening + Email Ingestion

**Completed since baseline:**

- ✅ **HttpOnly refresh-token cookie** — refresh token moved from `localStorage` to an `HttpOnly` `SameSite=Lax` cookie; no longer accessible to JavaScript (closes CR-S8)
- ✅ **Axios concurrent-refresh queue** — multiple simultaneous 401s serialised behind a single in-flight refresh promise, preventing duplicate logout (closes CR-S7)
- ✅ **CORS production validator** — `Settings.validate_secret_key` rejects wildcard / localhost-only `ALLOWED_ORIGINS` at startup in production (closes S-8)
- ✅ **Fernet-encrypted SMTP passwords** — `email_configs.smtp_password` encrypted at rest; key derived from `SECRET_KEY` (closes S-4 / CR-S3)
- ✅ **PDF attachment support** — `application/pdf` allowed via `%PDF` magic-byte detection; available in ticket creation, ticket detail, and email ingestion
- ✅ **Single-step ticket creation form** — optional fields (priority / category / group / assignee) hidden on mobile screens (≤ 640 px) for a compact experience
- ✅ **Email-to-ticket ingestion** (`email_ingestion.py` + `imap_poller.py`)
    - Background asyncio IMAP polling task (`run_forever` / configurable interval)
    - `[Ticket #N]` / `[Ticket-N]` / `[Ticket N]` bracket subject parsing (bare-word pattern excluded to avoid false positives)
    - Comment created from email body (HTML stripped; 50 000-char cap)
    - Attachments saved via `add_attachment_bytes` (magic-byte validated, 10 MB cap)
    - Sender resolved to registered + active + approved user; org-scope enforced
    - Admin endpoint `POST /admin/email-ingestion/poll` for manual trigger (superuser only)
- ✅ **IMAP security hardening** (10-issue internal review resolved)
    - 30 s connection timeout — prevents thread-pool starvation on hung server
    - 10 MB raw message size limit (`IMAP_MAX_MESSAGE_SIZE_MB`) — DoS guard before parsing
    - 50-part MIME-bomb guard in `extract_text_body` and `extract_file_parts`
    - Org-scope access control (`_resolve_author` returns `User`; caller checks `organization_id`)
    - 50 000-char comment body cap
    - 255-char filename truncation in `add_attachment_bytes`
    - `_mark_seen` decoupled from DB transaction (prevents duplicate comments on IMAP network blip)
    - `IMAP_USE_SSL=False` blocked at startup in production by `model_validator`
    - `sender_prefix` shown only in system-user fallback mode (permissive mode)

**Counts:**

| Metric | Before | After |
|--------|--------|-------|
| Backend tests passing | 66 | 66 |
| Security items resolved (arch + code review combined) | 0 | 6 + 10 IMAP |
| New services | — | `email_ingestion.py`, `imap_poller.py` |
| New config vars | — | 11 `IMAP_*` vars |

---

## 15. Recommendations

### Near-term (next 1–3 features)

1. **Implement outbound email notifications** — The SMTP infrastructure is in place (`email_configs` model, per-org config UI, Fernet-encrypted credentials). The next step is a background task that sends mail on ticket creation, assignment, and status change. Use the same asyncio-task pattern as the IMAP poller.

2. **Add rate limiting to auth endpoints** — Use `slowapi` (Starlette/FastAPI compatible) on `POST /auth/login` and `POST /auth/password-reset/request`. A simple in-memory store is sufficient for single-instance deployments.

3. **Refresh token revocation** — Store issued refresh tokens (or a per-user `token_family` nonce) in the DB; invalidate on logout. Adds the missing server-side revocation layer now that client-side exfiltration is mitigated by HttpOnly cookies.

### Medium-term

4. **Pagination on ticket endpoints** — `GET /tickets/` and `GET /tickets/board` will become slow with large datasets. Add `limit`/`offset` or cursor-based pagination to the board endpoint and a summary-only board view for high-cardinality columns.

5. **Error boundaries in React** — Wrap page-level routes in `<ErrorBoundary>` to prevent full-app crashes on component errors.

6. **Mobile app completion** — Implement navigation stack, ticket detail screen, and create-ticket form as the minimum viable mobile feature set.

### Long-term

7. **Real-time updates** — Replace the 30-second polling with `WebSocket` or `Server-Sent Events` for the Kanban board. FastAPI supports both natively.

9. **Deploy pipeline** — Add a `docker push` + `docker compose pull && up` step to `ci.yml` targeting a staging environment on every `master` push.
