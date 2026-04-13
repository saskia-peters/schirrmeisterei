# Ticketsystem — Architecture & Code Review

| Version | Date       | Author               | Notes                                |
|---------|------------|----------------------|--------------------------------------|
| 1.0     | 2026-04-12 | Architecture Reviewer + Code Reviewer (AI-assisted) | Initial review |
| 1.1     | 2026-04-12 | GitHub Copilot | Fixed C-1, C-2, A-9 (password reset token security) |
| 1.2     | 2026-04-13 | GitHub Copilot | Fixed C-3 (magic-byte validation on file uploads) |
| 1.3     | 2026-04-13 | GitHub Copilot | Fixed A-5, H-4, H-1 (authenticated attachment downloads) |
| 1.4     | 2026-04-13 | GitHub Copilot | Fixed A-2 (org hierarchy `GET /` requires authentication) |
| 1.5     | 2026-04-13 | GitHub Copilot | Fixed attachment delete regression (`import aiofiles.os`); added new findings N-1–N-13, NEW-1–NEW-3; added 500+ user scale-up action plan |
| 1.6     | 2026-04-13 | GitHub Copilot | Fixed S-1 (org-scope bypass on all ticket sub-resource endpoints) |
| 1.7     | 2026-04-13 | GitHub Copilot | Added SCALING.md; added env-configurable DB pool settings; added scale-up code comments; rescheduled roadmap for 20–30-user baseline |
| 1.8     | 2026-04-13 | GitHub Copilot | Fixed S-2 (comment update/delete now enforce `ticket_id` binding) |
| 1.9     | 2026-04-13 | GitHub Copilot | Fixed S-3 (TOTP replay prevention: `last_totp_code` + `last_totp_used_at` on User; migration 0003) |

---

## Management Summary

The ticketsystem is a well-structured, purpose-built incident and ticket management platform with a clean layered architecture (FastAPI backend, React frontend, PostgreSQL). The overall code quality and project organisation are **above average for an internal tool**, and the domain modelling is solid.

However, the system is **not ready for production deployment in its current state.** Independent architecture and code review processes identified **5 critical security vulnerabilities** that must be resolved before any public or multi-organisation rollout. Beyond the critical items, there are 9 high-severity findings (security, performance, reliability) and a number of medium/low improvements that are important for long-term maintainability.

The most urgent concerns are:

- **Password reset tokens are exposed in the API response** (even in development mode) — a direct credential leak attack vector.
- **File uploads are not validated for content** — an attacker can upload HTML/script files disguised as images, enabling stored XSS.
- **All uploaded attachments are publicly accessible** without any authentication — sensitive ticket documents can be accessed by anyone who guesses a URL.
- **Organisational hierarchy endpoints have no authentication** — any user can read your full org tree without being logged in.
- **Frontend authentication tokens are stored in `localStorage`** — a single XSS vulnerability can steal all user sessions.

A prioritised three-phase remediation roadmap follows the detailed findings below.

---

## Risk Summary

| # | Finding | Severity | Category | Effort |
|---|---------|----------|----------|--------|
| ~~C-1~~ | ~~Password reset token returned in API response~~ | ✅ Fixed 1.1 | Security | Low |
| ~~C-2~~ | ~~Password reset accepts any valid access token~~ | ✅ Fixed 1.1 | Security | Low |
| ~~C-3~~ | ~~File upload: no magic-byte / content-type validation~~ | ✅ Fixed 1.2 | Security | Medium |
| C-4 | `os.remove()` called blocking inside async handler | ~~🔴 Critical~~ ✅ Fixed | Reliability | Low |
| C-5 | Empty-string `organization_id` silently written to DB | ~~🔴 Critical~~ ✅ Fixed | Data Integrity | Low |
| A-1 | SMTP password stored as plaintext in config | ~~🔴 Critical~~ ✅ Fixed | Security | Low |
| ~~A-2~~ | ~~`GET /org` hierarchy endpoints unauthenticated~~ | ✅ Fixed 1.4 | Access Control | Low |
| ~~H-1~~ | ~~Attachment delete: file path not traversal-checked~~ | ✅ Fixed 1.3 | Security | Low |
| H-2 | Refresh token stored in `localStorage` (XSS risk) | 🔴 High | Security | Medium |
| H-3 | Race condition in concurrent token refresh | 🔴 High | Reliability | Medium |
| ~~H-4~~ | ~~`file_path` (internal server path) exposed in API~~ | ✅ Fixed 1.3 | Info Disclosure | Low |
| H-5 | Spurious `db.commit()` inside `get_db` session context | ~~🔴 High~~ ✅ Fixed | Reliability | Low |
| A-3 | `GET /tickets/{id}` missing org-scoped visibility check | 🔴 High | Access Control | Low |
| A-4 | No refresh token revocation (TOTP bypass vector) | 🔴 High | Security | Medium |
| ~~A-5~~ | ~~All uploaded attachments publicly accessible without authentication~~ | ✅ Fixed 1.3 | Access Control | Medium |
| A-6 | No rate limiting on login, TOTP, upload endpoints | 🟡 High | Security | Low |
| A-7 | No pagination on list/kanban endpoints | 🟡 High | Scalability | Medium |
| A-8 | N+1 query in `get_descendants` (org hierarchy BFS) | 🟡 High | Performance | Low |
| M-1 | `selectinload` blocks copy-pasted 3× in ticket service | 🟡 Medium | Maintainability | Low |
| M-2 | Model validators manually reconstruct full dicts | 🟡 Medium | Maintainability | Low |
| M-3 | `window.prompt()` for "Waiting for" reason in UI | 🟡 Medium | UX | Low |
| M-4 | Kanban filters compare by label name, not ID | 🟡 Medium | Correctness | Low |
| M-5 | `useUpdateTicket` closes over stale `ticketId` prop | 🟡 Medium | Correctness | Low |
| M-6 | Admin endpoints bypass service layer, use ORM directly | 🟡 Medium | Maintainability | Low |
| M-7 | `list_assignable_users` returns all users (no org scope) | 🟡 Medium | Access Control | Low |
| M-8 | No default `onError` in mutation hooks — silent failures | 🟡 Medium | UX / Observability | Low |
| ~~A-9~~ | ~~Dev password reset leaks token in response~~ | ✅ Fixed 1.1 | Info Disclosure | Low |
| A-10 | `ConfigItem` polymorphic table lacks type constraints | 🟡 Medium | Data Integrity | Medium |
| A-11 | Unassigned-org users create invalid tickets (FK error) | 🟡 Medium | Data Integrity | Low |
| A-12 | No structured logging or observability | 🟡 Medium | Operability | Medium |
| A-13 | DB connection pool uses default size (too small) | 🟡 Medium | Performance | Low |
| L-1–L-6 | Minor code style / UX inconsistencies | 🟢 Low | Code Quality | Low |
| **N-1** | **All ticket mutation endpoints lack org-scope check (A-3 scope extension)** | 🔴 Critical | Access Control | Low |
| **N-2** | **File attachments on local disk — HA blocker for horizontal scaling** | 🔴 Critical | High Availability | High |
| **N-3** | **DB pool default size (5) — exhausted under 500-user load** | 🔴 Critical | Performance | Low |
| **N-4** | **Eager-load of full ticket graph on every list/board request** | 🟠 High | Performance / Memory | Medium |
| **N-5** | **File upload buffers entire content before size check — DoS vector** | 🟠 High | Security / Reliability | Low |
| **N-6** | **SMTP password stored in plaintext in PostgreSQL (at-rest)** | 🟠 High | Cryptographic Failure | Medium |
| ~~**N-7**~~ | ~~**TOTP code replay not prevented within 30-second window**~~ ✅ Fixed v1.9 | ~~🟠 High~~ | Authentication | Low |
| **N-8** | **`/health` does not validate DB connectivity — misleads orchestrators** | 🟡 Medium | Operability | Low |
| **N-9** | **Single PostgreSQL instance — no HA, no failover** | 🔴 Critical | High Availability | High |
| **N-10** | **No shared cache/state layer — per-process rate limiting ineffective at scale** | 🟠 High | HA / Security | Medium |
| **N-11** | **`ALLOWED_ORIGINS` hardcoded to `localhost` in production compose** | 🟡 Medium | Security Misconfiguration | Low |
| **N-12** | **No structured logging or request correlation IDs** | 🟡 Medium | Operability | Medium |
| **N-13** | **PKs stored as `String(36)` text UUIDs instead of native PostgreSQL UUID** | 🟢 Low | Performance | Medium |
| **NEW-1** | **C-3 fix silently blocks non-image attachments (PDFs, etc.)** | 🟡 Medium | Correctness | Low |
| ~~**NEW-2**~~ | ~~**Comment update/delete don't enforce `ticket_id` FK in query**~~ ✅ Fixed v1.8 | ~~🔴 High~~ | Access Control | Low |
| **NEW-3** | **`/auth/refresh` bypasses TOTP on stolen refresh token** | 🔴 High | Authentication | Medium |

---

## Detailed Findings

### Section 1 — Critical Security Vulnerabilities

---

#### ~~C-1 · Password reset token returned in API response~~ ✅ Fixed in v1.1
> **Resolution:** Token is no longer returned in the API response. It is logged server-side at `DEBUG` level only (`logger.debug("Password reset token for %s: %s", email, token)`). The response always returns the same generic message.

**File:** [backend/app/api/v1/endpoints/auth.py](backend/app/api/v1/endpoints/auth.py)
**OWASP:** A02 – Cryptographic Failures

```python
if settings.ENVIRONMENT == "development":
    return {"message": "...", "reset_token": token}
```

The reset token (which is a full JWT access token — see C-2) is returned directly in the HTTP response. If `ENVIRONMENT` is not set correctly on staging or demo deployments, this exposes a live credential over the network. Logs and network traces (proxies, load-balancer access logs) will record it.

**Fix:** Remove the token from the response entirely. Log it server-side only via `logger.debug("reset_token=%s", token)`. Never return secrets in response bodies, even in development.

---

#### ~~C-2 · Password reset accepts any valid access token~~ ✅ Fixed in v1.1
> **Resolution:** Added `create_password_reset_token()` in `security.py` which issues a JWT with `type: "password_reset"` and a 1-hour expiry. `confirm_password_reset` now validates `payload.get("type") == "password_reset"`, rejecting all regular access tokens.

**File:** [backend/app/api/v1/endpoints/auth.py](backend/app/api/v1/endpoints/auth.py)
**OWASP:** A07 – Identification and Authentication Failures

The password reset flow issues and validates a regular `access` type JWT. Any currently-valid access token — from any session, for any purpose — is accepted as a reset token. An attacker who intercepts a session token can use it to reset the victim's password.

**Fix:** Issue a short-lived JWT with a dedicated `purpose: "password_reset"` claim and validate that claim when processing the reset request.

---

#### ~~C-3 · File upload: no magic-byte validation (content-type spoofing)~~ ✅ Fixed in v1.2
> **Resolution:** Both `add_attachment` (ticket attachments) and `upload_avatar` now use Pillow (`Image.open(io.BytesIO(bytes)).format`) to detect the actual file format from its magic bytes before accepting the upload. The client-supplied `Content-Type` header is ignored entirely. The server-detected MIME type (or canonical extension for avatars) is used for storage. HTML/script files disguised as images are rejected with HTTP 400.

**File:** [backend/app/services/ticket_service.py](backend/app/services/ticket_service.py) · [backend/app/api/v1/endpoints/users.py](backend/app/api/v1/endpoints/users.py)
**OWASP:** A03 – Injection / A08 – Software and Data Integrity Failures

File MIME type is read from the client-supplied `Content-Type` header without any server-side validation. An attacker can upload an HTML file containing `<script>` tags with `Content-Type: image/png`, which is then served back from the static file mount and executed by a victim's browser.

**Fix:** Use `python-magic` to inspect the first 512 bytes of the uploaded file and compare against an allowlist (`image/*`, `application/pdf`, etc.). Reject files where the detected type does not match the declared type.

---

#### ~~C-4 · `os.remove()` called blocking in async endpoint~~ ✅ Fixed 2026-04-13
**File:** [backend/app/services/ticket_service.py](backend/app/services/ticket_service.py)
**OWASP:** N/A — reliability

```python
os.remove(attachment.file_path)  # blocks the event loop
```

This call blocks the asyncio event loop for the duration of the filesystem operation. Under any significant request concurrency, this causes all other requests to stall.

> **Resolution:** Replaced both `os.path.exists()` and `os.remove()` in `delete_attachment` with their async equivalents from the already-imported `aiofiles` package: `await aiofiles.os.path.exists(...)` and `await aiofiles.os.remove(...)`. The event loop is no longer blocked during file deletion.

---

#### ~~C-5 · Empty-string `organization_id` silently written to ticket~~ ✅ Fixed 2026-04-13
**File:** [backend/app/services/ticket_service.py](backend/app/services/ticket_service.py#L96)
**OWASP:** A04 – Insecure Design

```python
organization_id=organization_id or "",
```

If `current_user.organization_id` is `None`, an empty string is persisted as the foreign key. This bypasses the DB FK constraint (since `""` is not a valid UUID), results in a `ForeignKeyViolationError` unhandled 500, or silently creates an unscoped ticket.

> **Resolution:** Added an explicit guard in `create_ticket` (tickets.py) that raises `HTTP 400` before calling the service when the user has no `organization_id`. Removed the silent `or ""` fallback in `TicketService.create` so the method signature now reflects the real invariant (`organization_id` must be a valid UUID when reached).

---

#### ~~A-1 · SMTP password stored in plaintext config~~ ✅ Fixed 2026-04-13
**File:** [backend/app/schemas/user.py](backend/app/schemas/user.py) / `EmailConfigCreate`, `EmailConfigUpdate`
**OWASP:** A02 – Cryptographic Failures

The SMTP password is stored as a plain string in the application config model. If the config is logged, serialised, or included in an error response, the credential is exposed.

> **Resolution:** `smtp_password` in `EmailConfigCreate` and `EmailConfigUpdate` changed from `str` to `SecretStr`. The two admin endpoints (`create_email_config`, `update_email_config`) now call `.get_secret_value()` only when writing to the SQLAlchemy model, so the secret is never present in serialised request payloads, logs, or tracebacks. `EmailConfigResponse` already omitted `smtp_password`, so the GET endpoints are unaffected. Note: at-rest encryption in the database (e.g. Fernet-based SQLAlchemy `TypeDecorator`) remains a follow-up hardening step.

---

#### ~~A-2 · Organisation hierarchy endpoints are unauthenticated~~ ✅ Fixed in v1.4
> **Resolution:** `GET /organizations/` (the catch-all list endpoint used by the authenticated admin panel) now requires `Depends(get_current_user)`. The three narrowly-scoped registration endpoints (`/landesverbaende`, `/regionalstellen`, `/ortsverbaende`) are intentionally left public — they expose only org names and IDs and are called by the registration form before a user token exists. Each endpoint now has a docstring that explicitly states its access policy.

**File:** [backend/app/api/v1/endpoints/organizations.py](backend/app/api/v1/endpoints/organizations.py)
**OWASP:** A01 – Broken Access Control

All GET endpoints under `/api/v1/organizations` are accessible without a valid token. Any external party can enumerate your full organisational structure, IDs, and hierarchy.

**Fix:** Add `current_user: User = Depends(get_current_user)` to all organisation router endpoints. Apply `Depends(require_superadmin)` to write operations.

---

### Section 2 — High-Severity Findings

---

#### ~~H-1 · Attachment delete: `file_path` not validated for path traversal~~ ✅ Fixed 2026-04-13
> **Resolution:** The `download_attachment` endpoint applies a path-traversal guard: `Path(attachment.file_path).resolve()` is checked to start with `Path(settings.UPLOAD_DIR).resolve()` before serving the file. The same guard has now been added to `delete_attachment` in `ticket_service.py`: if the resolved path escapes the upload root a `ForbiddenException` is raised and the file is never touched.

**File:** [backend/app/api/v1/endpoints/tickets.py](backend/app/api/v1/endpoints/tickets.py)
**OWASP:** A01 – Broken Access Control

The `file_path` stored in the database is passed directly to `os.remove()`. A database row with a crafted `file_path` (e.g. `../../etc/passwd`) could delete arbitrary files on the server.

**Fix:** Validate that the resolved path is inside the configured upload directory:
```python
upload_root = Path(settings.UPLOAD_DIR).resolve()
target = Path(attachment.file_path).resolve()
if not str(target).startswith(str(upload_root)):
    raise HTTPException(status_code=400, detail="Invalid attachment path")
```

---

#### H-2 · Refresh token stored in `localStorage` — XSS exfiltration
**File:** [frontend/src/…/auth](frontend/src/)
**OWASP:** A07 – Authentication Failures

Refresh tokens persisted in `localStorage` are fully accessible to JavaScript. A single XSS vulnerability (including one in any third-party npm dependency) allows an attacker to steal all user sessions silently.

**Fix:** Store the refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie set by the backend. The access token (short-lived) may stay in memory. This change requires a backend `/auth/refresh` endpoint that reads from the cookie rather than the request body.

---

#### H-3 · Race condition in concurrent token refresh
**File:** [frontend/src/hooks/useApi.ts](frontend/src/hooks/useApi.ts) (or axios interceptor)
**OWASP:** A07 – Authentication Failures

When multiple API calls fire simultaneously and the access token has expired, each call independently attempts a token refresh. This causes multiple parallel `/auth/refresh` requests — most of which will fail once the first one rotates the refresh token, logging the user out unexpectedly.

**Fix:** Implement a `refreshPromise` singleton: if a refresh is already in flight, queue subsequent requests to await the same promise rather than issuing new refresh calls.

---

#### ~~H-4 · `file_path` (internal server filesystem path) exposed in API response~~ ✅ Fixed in v1.3
> **Resolution:** `file_path` has been removed from `AttachmentResponse`. The schema now exposes only `url` (a computed field pointing to the authenticated download endpoint), `filename`, `content_type`, `file_size`, and metadata IDs. Internal server paths are no longer visible to any client.

**File:** [backend/app/schemas/ticket.py](backend/app/schemas/ticket.py) — `AttachmentResponse`
**OWASP:** A05 – Security Misconfiguration

The response schema includes the full server-side path (e.g. `/app/uploads/attachments/abc.jpg`). This reveals the container's internal directory structure, aiding server enumeration attacks.

**Fix:** Exclude `file_path` from the response schema. Expose only `download_url` (a relative or signed URL) and `file_name`.

---

#### ~~H-5 · Spurious `db.commit()` inside `get_db` session context~~ ✅ Fixed 2026-04-13
**File:** [backend/app/db/session.py](backend/app/db/session.py)
**OWASP:** N/A — data integrity

A `db.commit()` call appears inside the `get_db` dependency generator, causing every request to auto-commit even if the handler raised an exception and the commit should have been rolled back. This can leave partially-written data in the database.

> **Resolution:** `get_db` in `session.py` already wraps the commit in a `try/except`: commit runs only on success, and `session.rollback()` is called on any exception before re-raising — this is the correct transaction-boundary pattern. The remaining issue was an explicit `await db.commit()` at the end of the `bulk_upload_hierarchy` endpoint in `admin.py` (line 884), which double-committed and could bypass the session's rollback guarantee if subsequent code raised after the early commit. That redundant commit has been removed; `get_db` is now the single commit boundary for all endpoints.

---

#### A-3 · `GET /tickets/{id}` missing org-scoped visibility check
**File:** [backend/app/api/v1/endpoints/tickets.py](backend/app/api/v1/endpoints/tickets.py)
**OWASP:** A01 – Broken Access Control

The list/kanban endpoints correctly scope results to the caller's organisation hierarchy. However, the single-ticket `GET /tickets/{id}` endpoint fetches by UUID alone, allowing any authenticated user to read any ticket in the system if they know its ID.

**Fix:** After fetching the ticket, verify `ticket.organization_id in await org_svc.get_visible_org_ids(current_user)` and return 404 on mismatch (not 403, to avoid confirming existence).

---

#### A-4 · No refresh token revocation (TOTP bypass vector)
**File:** [backend/app/api/v1/endpoints/auth.py](backend/app/api/v1/endpoints/auth.py)
**OWASP:** A07 – Authentication Failures

Refresh tokens are pure JWTs with no server-side revocation list. If a user enables TOTP after an active session, existing refresh tokens bypass the TOTP challenge to silently obtain new access tokens.

**Fix:** Store refresh token JTI in the database on issuance, and delete the row on logout or TOTP enable. On refresh, verify the JTI is still in the table before issuing a new access token.

---

#### ~~A-5 · All uploaded attachments publicly accessible without authentication~~ ✅ Fixed in v1.3
> **Resolution:**
> - The broad `StaticFiles("/uploads")` mount has been replaced with a narrow `StaticFiles("/uploads/avatars")` mount that serves only avatar images (low-sensitivity profile photos).
> - Ticket attachments are now served exclusively via `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download`, which requires a valid `Bearer` token (`get_current_user` dependency). The endpoint also applies a path-traversal guard before serving the file (H-1).
> - The `AttachmentResponse` schema `url` field now points to this authenticated endpoint. `file_path` is removed from the schema entirely (H-4).
> - The frontend `AttachmentThumb` component fetches image data via the authenticated `apiClient` (which adds the `Authorization` header) and renders using an Object URL, since `<img src>` and `<a href>` do not send Bearer tokens on their own.

**Files:** [backend/app/main.py](backend/app/main.py) · [backend/app/api/v1/endpoints/tickets.py](backend/app/api/v1/endpoints/tickets.py) · [backend/app/schemas/ticket.py](backend/app/schemas/ticket.py) · [frontend/src/components/tickets/AttachmentThumb.tsx](frontend/src/components/tickets/AttachmentThumb.tsx)
**OWASP:** A01 – Broken Access Control

```python
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
```

Any person who can guess or discover a file URL (e.g. via a browser history, link share, or guessing the UUID pattern) can download sensitive ticket attachments without logging in.

**Fix:** Remove the `StaticFiles` mount. Serve attachments through an authenticated endpoint that verifies org-scoped access and then streams the file.

---

#### A-6 · No rate limiting on login, TOTP, and upload endpoints
**File:** [backend/app/api/v1/endpoints/auth.py](backend/app/api/v1/endpoints/auth.py)
**OWASP:** A05 – Security Misconfiguration

The login endpoint has no request rate limit, enabling credential-stuffing attacks. TOTP has only 1 million combinations (6 digits) and can be brute-forced without limit. Upload endpoints can be abused for storage exhaustion.

**Fix:** Add `slowapi` (wraps `limits` library):
```python
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, ...): ...
```
Apply `5/minute` to login, `3/minute` to TOTP verify, `20/minute` to uploads.

---

#### A-7 · No pagination on ticket list or Kanban endpoints
**File:** [backend/app/api/v1/endpoints/tickets.py](backend/app/api/v1/endpoints/tickets.py#L57)
**OWASP:** N/A — scalability

`list_tickets`, `get_kanban_board`, and `list_users` fetch all records with all relationships eagerly loaded. With a few thousand tickets (each with comments, attachments, and status logs), this results in gigabytes of data per request, causing memory exhaustion and frontend rendering freezes.

**Fix:** Add `skip: int = 0, limit: int = 100` parameters. For the Kanban board, return `TicketSummary` objects only (defer comments/attachments to a per-ticket lazy load). Use cursor-based pagination keyed on `ticket_number` for the list view.

---

#### A-8 · N+1 query in `get_descendants` (org hierarchy BFS)
**File:** [backend/app/services/organization_service.py](backend/app/services/organization_service.py#L49)
**OWASP:** N/A — performance

```python
async def get_descendants(self, org_id: str) -> list[str]:
    queue = [org_id]
    while queue:
        current = queue.pop(0)
        children = await self.list_children(current)  # DB query per node
```

For a 4-level hierarchy with 1,000+ leaf organisations, this issues 1,000+ sequential queries for every ticket list request by a superadmin.

**Fix:** Replace with a single recursive CTE:
```python
cte = text("""
    WITH RECURSIVE tree AS (
        SELECT id FROM ticketsystem.organizations WHERE id = :root
        UNION ALL
        SELECT o.id FROM ticketsystem.organizations o
        JOIN tree t ON o.parent_id = t.id
    )
    SELECT id FROM tree
""")
result = await self.db.execute(cte, {"root": org_id})
return [row[0] for row in result.fetchall()]
```

---

### Section 3 — Medium-Severity Findings

| ID | Finding | File | Fix |
|----|---------|------|-----|
| M-1 | `selectinload` blocks copy-pasted 3× in ticket service | [ticket_service.py](backend/app/services/ticket_service.py) | Extract to a `_ticket_options()` helper function |
| M-2 | Model validators manually reconstruct full dicts (fragile on new fields) | [schemas/ticket.py](backend/app/schemas/ticket.py) | Use Pydantic `mode="wrap"` validator or computed fields |
| M-3 | `window.prompt()` for "Waiting for" reason — inconsistent with rest of UI | [TicketDetail.tsx](frontend/src/components/tickets/TicketDetail.tsx) | Replace with inline modal textarea (same pattern as KanbanBoard) |
| M-4 | Kanban priority/category/group filters compare by label name, not ID | [KanbanBoard.tsx](frontend/src/components/board/KanbanBoard.tsx) | Store config item `id` in filter state; compare `t.priority_id === filterPriority` |
| M-5 | `useUpdateTicket` closes over stale `ticketId` prop | [useApi.ts](frontend/src/hooks/useApi.ts) | Pass `id` in mutation payload; use `variables.id` in `onSuccess` |
| M-6 | Admin endpoints bypass service layer and call ORM directly | [admin.py](backend/app/api/v1/endpoints/admin.py) | Move config-item CRUD into a `ConfigService` |
| M-7 | `list_assignable_users` returns all users across all orgs | [users.py](backend/app/api/v1/endpoints/users.py) | Scope to caller's org hierarchy using `get_visible_org_ids` |
| M-8 | No default `onError` in mutation hooks — errors silently swallowed | [useApi.ts](frontend/src/hooks/useApi.ts) | Add a default `onError: (e) => toast.error(...)` to each mutation |
| ~~A-9~~ | ~~Dev password reset leaks token in response body~~ ✅ Fixed v1.1 | [auth.py](backend/app/api/v1/endpoints/auth.py) | Resolved by C-1 fix — token logged server-side only |
| A-10 | `ConfigItem` polymorphic table has no DB-level type constraint | [models.py](backend/app/models/models.py) | Validate `item.type` matches expected type in service layer |
| A-11 | User without org assignment causes unhandled 500 on ticket creation | [ticket_service.py](backend/app/services/ticket_service.py) | Validate `current_user.organization_id` at endpoint entry |
| A-12 | No structured logging or security event observability | project-wide | Add `structlog` + JSON log formatter; log failed logins, permission denials |
| A-13 | DB connection pool uses default size (too small for concurrent load) | [session.py](backend/app/db/session.py) | Set `pool_size=10, max_overflow=20, pool_recycle=1800` |

---

### Section 4 — Low-Severity Findings

| ID | Finding | File |
|----|---------|------|
| L-1 | `UserCreate` re-imported inside function body in `admin.py` | [admin.py](backend/app/api/v1/endpoints/admin.py) |
| L-2 | `user_svc._user_options()` called from outside the service (breaks encapsulation) | [admin.py](backend/app/api/v1/endpoints/admin.py) |
| L-3 | `is_approved=False` default not documented in schema | [schemas/user.py](backend/app/schemas/user.py) |
| L-4 | Hardcoded `"helfende"` string in 6+ places instead of `UserGroupName.HELFENDE.value` | multiple |
| L-5 | Status `<select>` in TicketDetail not disabled while mutation is pending | [TicketDetail.tsx](frontend/src/components/tickets/TicketDetail.tsx) |
| L-6 | `LoginPage.tsx` manages loading state manually instead of using `useMutation` | [LoginPage.tsx](frontend/src/components/auth/LoginPage.tsx) |

---

### Section 5 — Test Coverage Gaps

| Area | Status | Priority |
|------|--------|----------|
| Permission enforcement (e.g. close ticket without `close_ticket` role) | ❌ Missing | Critical |
| Backend `admin.py` endpoints (approvals, config items, group management) | ❌ Missing | High |
| Backend `users.py` (avatar upload, access control) | ❌ Missing | High |
| Frontend `TicketDetail` (status change, comment CRUD, attachment upload) | ❌ Missing | High |
| Frontend `KanbanBoard` (filter logic, drag-and-drop) | ❌ Missing | High |
| Backend `TicketService` unit tests (currently integration-only) | 🟡 Partial | Medium |
| Frontend `CreateTicketModal` error path | 🟡 Partial | Medium |
| Backend TOTP brute-force / invalid code scenarios | 🟡 Partial | Medium |

**Highest priority gap:** A test verifying that a user without the `close_ticket` permission receives HTTP 403 from `PATCH /tickets/{id}/status` with `status=closed`. This permission check is a core business rule and is currently unverified by any test.

---

## Improvement Roadmap

### Phase 1 — Before Any Production Deployment (Blockers)

These items represent active security vulnerabilities or data-integrity risks. **Do not deploy publicly without addressing these.**

1. **Fix password reset flow (C-1, C-2, A-9) ✅ Done:** Token no longer returned in response; dedicated `password_reset` JWT type used.
2. **Add magic-byte validation on uploads (C-3) ✅ Done:** Pillow magic-byte detection in `add_attachment` and `upload_avatar`; `Content-Type` header ignored.
3. **Make file downloads authenticated (A-5) ✅ Done:** `StaticFiles` mount narrowed to avatars only; attachments served via auth endpoint; `AttachmentThumb` fetches blobs via apiClient. Also resolved H-4 and H-1.
4. **Authenticate org endpoints (A-2) ✅ Done:** `GET /organizations/` requires auth. Registration-dropdown endpoints remain public by design.
5. ~~**Fix empty-string org_id guard (C-5):** Validate `organization_id` at the endpoint level before calling the service.~~ ✅ Done
6. ~~**Protect SMTP credentials (A-1):** Use Pydantic `SecretStr` for `smtp_password`.~~ ✅ Done
7. ~~**Fix blocking `os.remove` (C-4):** Replace with `await asyncio.to_thread(os.remove, ...)`.~~ ✅ Done
8. ~~**Remove `file_path` from API response (H-4):** Expose only `download_url` and `file_name`.~~ ✅ Done (v1.3)
9. ~~**Remove spurious `db.commit()` in `get_db` (H-5):** Commits must be explicit in service methods only.~~ ✅ Done
10. ~~**Fix path traversal check on attachment delete (H-1):** Validate resolved path is within upload root.~~ ✅ Done

---

### Phase 2 — Short Term (Within 2–4 Sprints)

Address the remaining high-severity and most impactful medium findings.

11. **Move refresh tokens to `HttpOnly` cookie (H-2):** Requires backend `/auth/refresh` to read from cookie.
12. **Fix concurrent token refresh race condition (H-3):** Implement a `refreshPromise` singleton in the Axios interceptor.
13. **Add refresh token revocation (A-4):** Store JTI in DB; check on refresh; delete on logout or TOTP enable.
14. **Add org-scope check to `GET /tickets/{id}` (A-3):** Verify ticket org is in caller's visible hierarchy.
15. **Scope `list_assignable_users` to org hierarchy (M-7):** Apply `get_visible_org_ids` filter.
16. **Add rate limiting (A-6):** Install `slowapi`; apply to `/login`, `/auth/totp/verify`, upload endpoints.
17. **Implement pagination (A-7):** Add `skip/limit` to list endpoints; use `TicketSummary` for Kanban.
18. **Replace N+1 org query with recursive CTE (A-8):** Single DB round-trip for org hierarchy.
19. **Add `onError` defaults to mutation hooks (M-8):** Surface errors to users via toast or inline message.
20. **Write permission enforcement tests (test coverage):** At minimum, one test per role-gated endpoint.

---

### Phase 3 — Medium Term (Next Quarter)

Sustainability, observability, and developer experience improvements.

21. **Structured logging (A-12):** Add `structlog` with JSON output; log security events (failed logins, permission denials).
22. **Tune DB connection pool (A-13):** Set explicit `pool_size`, `max_overflow`, and `pool_recycle` values.
23. **Refactor selectinload duplication (M-1):** Extract `_ticket_options()` helper.
24. **Fix model validator fragility (M-2):** Use Pydantic `mode="wrap"` or computed properties.
25. **Fix stale closure in `useUpdateTicket` (M-5):** Pass `id` in mutation payload, use `variables.id` in `onSuccess`.
26. **Replace `window.prompt()` with inline modal (M-3):** Consistent UX for "Waiting for" reason input.
27. **Fix Kanban config-item filters (M-4):** Compare by ID, not by display name.
28. **Move admin config-item CRUD to `ConfigService` (M-6):** Consistent service layer pattern.
29. **Validate ConfigItem type on assignment (A-10):** Prevent categories being used as priorities.
30. **Expand test coverage (see Section 5):** Admin endpoints, `users.py`, `TicketDetail`, `KanbanBoard`.

---

## Scale-Up Action Plan — 500+ Concurrent Users

> **v2.2 — Updated 2026-04-13. S-6 (SMTP password encryption) fixed.**
>
> The system is currently deployed for **20–30 concurrent users** on a single-instance stack.
> Infrastructure-heavy items (object storage, managed HA PostgreSQL, Redis, PgBouncer) are
> **intentionally deferred** — they are not needed at this scale and would add unnecessary
> operational burden.  All deferred items are annotated with `⏸ Deferred` below.
>
> For the step-by-step growth guide (what to do at 50 / 100 / 300 / 500 users), configuration
> values, and exact file locations, see **[SCALING.md](SCALING.md)**.
>
> Code comments tagged `SCALE-UP` throughout the codebase point directly to the spots that
> need to change when a tier boundary is crossed.

---

### Tier 0 — Security Blockers (Fix before any deployment, regardless of scale)

These remain active vulnerabilities at any user count:

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| ~~S-1~~ | ~~**N-1 / A-3** — All ticket sub-resource endpoints bypass org-scope~~ ✅ Fixed v1.6 | ~~Add `_assert_ticket_visible(ticket, user, db)` helper called after every `get_by_id_or_raise`; return 404 on mismatch~~ | Low |
| ~~S-2~~ | ~~**NEW-2** — Comment update/delete don't bind to `ticket_id`~~ ✅ Fixed v1.8 | ~~Add `Comment.ticket_id == ticket.id` constraint to `update_comment` / `delete_comment` queries in `ticket_service.py`~~ | Low |
| ~~S-3~~ | ~~**N-7** — TOTP code replay within 30-second window~~ ✅ Fixed v1.9 | ~~Add `last_totp_code` + `last_totp_used_at` columns to `User`; reject reuse in `verify_totp`~~ | Low + 1 migration |
| ~~S-4~~ | ~~**A-4 / NEW-3** — No refresh token revocation; TOTP bypassed via stolen refresh token~~ ✅ Fixed v2.0 | ~~Store JTI in a `refresh_tokens` table (or Redis set with TTL); check JTI on every `/auth/refresh`; delete on logout / TOTP enable~~ | Medium |
| ~~S-5~~ | ~~**A-6** — No rate limiting on login, TOTP, reset endpoints~~ ✅ Fixed v2.1 | ~~Add `slowapi` + Redis backend; apply `@limiter.limit("10/minute")` to `/auth/login`, `/auth/totp/verify`, `/auth/password-reset/request`~~ | Low |
| ~~S-6~~ | ~~**N-6** — SMTP password plaintext in DB (A-1 partially fixed)~~ ✅ Fixed v2.2 | ~~Add SQLAlchemy `TypeDecorator` (Fernet, key from `SECRET_KEY` via HKDF) for `smtp_password` column; one-time data migration~~ | Medium |
| ~~S-7~~ | ~~**H-2** — Refresh token in `localStorage` — XSS exfiltration~~ ✅ Fixed v2.3 | ~~Move refresh token to `HttpOnly; Secure; SameSite=Strict` cookie; `/auth/login` and `/auth/refresh` set cookie and return only `access_token` in body; `/auth/logout` clears cookie; `refreshToken` removed from Zustand store and `localStorage` persistence; `COOKIE_SECURE` config flag (must be `True` in production)~~ | Medium |
| ~~S-8~~ | ~~**H-3** — Race condition in concurrent token refresh~~ ✅ Fixed v2.4 | ~~Add `refreshPromise` singleton in Axios interceptor (`client.ts`); concurrent 401s queue onto the same in-flight refresh call; promise cleared in `.finally()` so the next genuine expiry starts a fresh refresh~~ | Low |
| S-9 | **N-11** — `ALLOWED_ORIGINS` hardcoded `localhost` in production compose | Move to `ALLOWED_ORIGINS` env var with no default; fail startup in production if unset; restrict `allow_methods` to `["GET","POST","PATCH","DELETE","OPTIONS"]` | Low |

---

### Tier 1 — HA Blockers (Required before horizontal scaling)

These block zero-downtime deployment, multi-replica operation, or disaster recovery:

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| H-1 | **N-2** — Local disk storage not shared across replicas | Migrate to **MinIO** (self-hosted, S3-compatible) or AWS S3/GCS. Replace `aiofiles.open` + `FileResponse` with `aioboto3` `put_object` / pre-signed URL. Add `STORAGE_BACKEND` config. | High |
| H-2 | **N-3** — DB pool `pool_size=5` — exhausted under 500-user load | Set `pool_size=20, max_overflow=30, pool_timeout=30, pool_recycle=1800, pool_pre_ping=True` in `session.py`; make values env-configurable | Low (1-line fix) |
| H-3 | **N-9** — Single PostgreSQL instance — SPOF | Use a managed PostgreSQL with Multi-AZ (RDS, Cloud SQL) or deploy Patroni + HAProxy. Add `DATABASE_READ_URL` for read replicas. | High (Infra) |
| H-4 | **N-10** — No Redis — per-process rate limiting broken at scale | Add `redis:7` service to `docker-compose.yml`; wire to `slowapi` (S-5) and JTI store (S-4); cache org-hierarchy lookups (5-min TTL, invalidate on org write) | Medium |
| H-5 | **N-8** — `/health` always returns 200 | Add `/readiness` endpoint with `SELECT 1` DB ping (for orchestrator routing); keep `/health` as simple `/liveness` (no DB, fast crash-loop detection) | Low |
| H-6 | **PgBouncer** — DB connection fan-in | Deploy PgBouncer in transaction mode in front of PostgreSQL. The backend pool speaks to PgBouncer; PgBouncer caps server-side connections at PostgreSQL's `max_connections` (set to 200). This allows 50+ backend pool connections without exploding the DB server. | Medium (Infra) |

---

### Tier 2 — Performance (Required to sustain 500 users at acceptable latency)

At 20–30 users the current eager-load and BFS patterns are fine.  Add pagination (P-1) early — it is cheap and prevents regressions as ticket volume grows.

| # | Finding | Action | Effort | Phase |
|---|---------|--------|--------|-------|
| P-1 | **A-7** — No pagination | Add `skip: int = 0, limit: int = 100` to `list_all`, `list_by_status`, Kanban board. Cap `limit` at 200 server-side. Return `PaginatedResponse[TicketSummary]`. | Medium | Do early — cheap, prevents DoS as ticket count grows |
| P-2 | **A-8 + N-4** — N+1 org query + eager-load of full graph on every list | Replace BFS org lookup with PostgreSQL recursive CTE. Split into `_ticket_summary_options()` / `_ticket_detail_options()`. See `SCALE-UP` comment in `ticket_service.py`. | Medium | ⏸ Deferred — needed at 100+ users |
| P-3 | **N-4** — Kanban board loads all relationships | Kanban endpoint returns `TicketSummary` only. See `SCALE-UP` comment in `ticket_service.py`. | Medium | ⏸ Deferred — needed at 100+ users |
| P-4 | **N-5** — Upload buffers full file before size check | Read in chunks (see `SCALE-UP` comment in `ticket_service.py`). Add `client_max_body_size 11M;` to `nginx.conf` (commented out, ready to enable). | Low | Do when raising `MAX_UPLOAD_SIZE_MB` |
| P-5 | **N-10** (caching) | Cache `get_visible_org_ids` in Redis with 5-min TTL per org ID, invalidate on org write. | Medium | ⏸ Deferred — requires Redis (H-4) |
| P-6 | **N-13** — Text UUID PKs | Migrate PKs to PostgreSQL native `UUID` type. Pure Alembic migration. | Medium (Migration) | ⏸ Deferred — do during a planned maintenance window before traffic spikes |

---

### Tier 3 — Operability (Required to operate a 500-user system safely)

| # | Finding | Action | Effort |
|---|---------|--------|--------|
| O-1 | **N-12 / A-12** — No structured logging | Add `structlog` with JSON output. Add `asgi-correlation-id` middleware for `X-Request-ID` propagation. Log: `login.success`, `login.failure`, `token.refresh`, `permission.denied`, `totp.fail`, `attachment.upload`, `ticket.status_change`. | Medium |
| O-2 | **NEW-1** — C-3 fix blocks all non-image attachments | Decide: images-only (document explicitly, improve error message) **or** extend to PDFs (add `_detect_pdf_mime` via magic bytes `%PDF`). Either way, the product decision must be made now before users hit this. | Low |
| O-3 | **M-8** — Silent mutation failures | Add default `onError` toast handler in `useApi.ts` base mutations. One implementation, covers all 25+ mutation hooks. | Low |
| O-4 | **A-10** — `ConfigItem` polymorphism without type constraints | Add a `CHECK` constraint or trigger to prevent `category` items being assigned as `priority`. | Low + Migration |
| O-5 | **Section 5 test gaps** | At minimum: permission enforcement test per role-gated endpoint; org-scope bypass test for ticket sub-resources (verify the S-1 fix); TOTP replay prevention test. | Medium |
| O-6 | Dependency audit | Run `uv audit` (backend) and `pnpm audit` (frontend) before production; fix any CVEs. Pin all dependency versions in lockfiles. | Low (ongoing) |

---

### Summary: Critical Path to 500-User Production

For the full growth guide including trigger conditions and exact config values see **[SCALING.md](SCALING.md)**.

```
S-1 → S-4 → S-5         (security must be clean before going live)
  ↓         ↓
H-2 → H-4 → H-1         (HA: Redis → object storage — longest lead time)
              ↓
          H-3 / H-6      (managed DB + PgBouncer)
              ↓
     P-1 → P-2 → P-3     (pagination + query optimisation)
              ↓
          O-1 → O-5       (observability + tests)
```

**Minimum viable production set** (can go live with 500 users once these are done):
S-1, S-3, S-4, S-5, S-7, S-9, H-2, H-4, H-5, H-6, P-1, P-4, O-2

**Hard HA blockers** (horizontal scaling physically impossible without these):
H-1 (object storage), H-3 (managed DB), H-4 (Redis)

---

## How to Update This Document

This document is intended to be a living record of the system's quality posture. Update it after each significant sprint or review cycle:

1. **Mark resolved findings** by striking through the row in the risk table and adding a "Resolved in vX.Y" note.
2. **Add new findings** discovered during development or review by appending to the relevant section and creating a new row in the risk table.
3. **Re-run the architecture and code review agents** (via GitHub Copilot) to generate an updated findings list. Instructions:
   - Open the command palette → **GitHub Copilot: Open Agent Mode**
   - Run the `architecture-reviewer` agent with the prompt: *"Review the current state of the ticketsystem backend and frontend for architectural quality and security issues. Compare against the previous findings in REVIEW.md and identify what has been fixed and what new issues have appeared."*
   - Run the `code-reviewer` agent with the same context instruction.
   - Incorporate updated findings into this document, incrementing the version table at the top.
4. **Keep the roadmap in sync** — after completing a phase, move resolved items to a "Completed" appendix and promote Phase 2 items to Phase 1 as appropriate.
5. **Update the version table** at the top of this document whenever you make a revision.

---

*Last reviewed by: Architecture Reviewer + Code Reviewer agents (AI-assisted) on 2026-04-12.*
*Next scheduled review: after Phase 1 remediation is complete.*
