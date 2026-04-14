# Code Review

!!! info "Living Document"
    This document is updated with each significant review pass. Add a row to the [Review History](#review-history) table and a dated section to the [Progress Tracker](#progress-tracker) as issues are resolved.

---

## Review History

| Date | Reviewer | Files Read | Issues Found | Status |
|------|----------|-----------|--------------|--------|
| 2026-04-06 | Initial full review | 55 files, ~9 100 lines | 29 | 🔴 Open |
| 2026-04-13 | Security hardening pass | 8 files reviewed | 10 IMAP issues found + 2 CR-S closed | 🟡 Maturing |

---

## 1. Module Size Inventory

All source files were read and line-counted. Files exceeding 300 lines are flagged as candidates for splitting.

### Backend

| File | Lines | Flag |
|------|-------|------|
| `backend/app/api/v1/endpoints/admin.py` | **641** | ⚠ Split candidate |
| `backend/app/models/models.py` | **362** | ⚠ Large (acceptable for now) |
| `backend/app/api/v1/endpoints/auth.py` | 226 | ✅ |
| `backend/app/api/v1/endpoints/tickets.py` | 246 | ✅ |
| `backend/app/schemas/user.py` | 276 | ✅ |
| `backend/app/schemas/ticket.py` | 231 | ✅ |
| `backend/app/services/ticket_service.py` | **~380** | ⚠ Grown with `add_attachment_bytes`; still manageable |
| `backend/app/services/email_ingestion.py` | **~310** | ⚠ New file; within acceptable range |
| `backend/app/services/imap_poller.py` | **~165** | ✅ |
| `backend/app/services/user_service.py` | 176 | ✅ |
| `backend/app/services/organization_service.py` | 114 | ✅ |
| `backend/app/tests/integration/test_tickets.py` | 266 | ✅ |
| `backend/app/tests/conftest.py` | 157 | ✅ |
| `alembic/versions/0001_initial.py` | **320** | ⚠ Expected for squashed migration |
| `alembic/versions/0002_multi_tenancy.py` | **300** | ⚠ Expected for squashed migration |
| `alembic/versions/0003_user_avatar.py` | 24 | ✅ |
| Everything else | <200 | ✅ |

### Frontend

| File | Lines | Flag |
|------|-------|------|
| `frontend/src/components/admin/AdminPanel.tsx` | **1 029** | 🔴 Split urgently |
| `frontend/src/components/tickets/TicketDetail.tsx` | **507** | ⚠ Split candidate |
| `frontend/src/components/auth/ProfilePage.tsx` | **364** | ⚠ Borderline |
| `frontend/src/hooks/useApi.ts` | **358** | ⚠ Acceptable (logical organisation) |
| `frontend/src/types/index.ts` | **302** | ⚠ Acceptable (single type source) |
| `frontend/src/components/board/KanbanBoard.tsx` | 282 | ✅ |
| `frontend/src/api/index.ts` | 241 | ✅ |
| Everything else | <200 | ✅ |

### Mobile

| File | Lines | Flag |
|------|-------|------|
| `mobile/src/screens/TicketListScreen.tsx` | 91 | ✅ |
| `mobile/src/api/index.ts` | 67 | ✅ |
| `mobile/src/types/index.ts` | 55 | ✅ |

---

## 2. Functions / Methods Over 50 Lines

| Location | ~Lines | Issue |
|----------|--------|-------|
| `admin.py` — `upload_hierarchy()` | ~80 | DB writes and XLSX parsing inline in handler |
| `admin.py` — `bulk_upload_users()` | ~75 | Same — business logic belongs in a service |
| `AdminPanel.tsx` — `EmailConfigAdmin()` | ~160 | Inline table + create/edit form — should be its own component |
| `AdminPanel.tsx` — `UserRoleAdmin()` | ~130 | User–group assignment matrix inlined — should be its own component |
| `TicketDetail.tsx` — `TicketDetail()` | ~350 | Monolithic — see §6 |
| `ProfilePage.tsx` — `TwoFactorSection()` | ~100 | Manageable but would benefit from extraction |
| `alembic/0002_multi_tenancy.py` — `upgrade()` | ~120 | Expected; seed data in a single migration function |
| `ticket_service.py` — `update()` | ~55 | Long due to assignee change logging |

---

## 3. Security & Correctness Bugs

!!! danger "These items should be fixed before any production deployment."

### CR-S1 — Synchronous file write blocks the async event loop

**File:** [`backend/app/api/v1/endpoints/users.py`](../backend/app/api/v1/endpoints/users.py) ~line 118

The avatar upload handler uses a blocking `open()` call inside an `async def` endpoint:

```python
# ❌ Blocks the entire event loop under concurrent load
with open(filepath, "wb") as fh:
    fh.write(content)
```

The attachment upload in `ticket_service.py` correctly uses `aiofiles`. The avatar endpoint must be updated to match:

```python
# ✅
import aiofiles
async with aiofiles.open(filepath, "wb") as fh:
    await fh.write(content)
```

**Severity:** Medium — no data loss, but degrades throughput under concurrent requests.
**Status:** 🔴 Open

---

### CR-S2 — Avatar delete path not validated against UPLOAD_DIR

**File:** [`backend/app/api/v1/endpoints/users.py`](../backend/app/api/v1/endpoints/users.py)

```python
# ❌ No path-containment check before os.remove()
rel_path = current_user.avatar_url.lstrip("/")
os.remove(rel_path)
```

The value comes from the database (server-controlled), so the current risk is low. But writing the value via a direct `lstrip("/")` → `os.remove()` pattern is unsafe — defence in depth should verify the resolved path is inside `UPLOAD_DIR` before deletion:

```python
# ✅
resolved = Path(settings.UPLOAD_DIR, rel_path).resolve()
assert resolved.is_relative_to(Path(settings.UPLOAD_DIR).resolve())
os.remove(resolved)
```

**Severity:** Low (server-controlled input), pattern is unsafe.
**Status:** 🔴 Open

---

### CR-S3 — SMTP password stored in plain text

**File:** [`backend/app/models/models.py`](../backend/app/models/models.py) — `EmailConfig.smtp_password`

`smtp_password` is a plain `String(255)` column. Any person with `SELECT` access on the database retrieves all SMTP credentials in cleartext. Encrypt at rest using a key derived from `SECRET_KEY`:

```python
# Suggested: use cryptography.fernet, store as bytes or base64 string
```

**Severity:** Medium — credential exposure risk.
**Status:** 🔴 Open

---

### CR-S4 — Password reset token returned in API response body

**File:** [`backend/app/api/v1/endpoints/auth.py`](../backend/app/api/v1/endpoints/auth.py)

```python
if settings.ENVIRONMENT == "development":
    return {"message": "...", "reset_token": token}
```

`ENVIRONMENT` defaults to `"development"` in `config.py`. If the env var is not set in staging or production, a valid password-reset token is exposed in the response body. The guard works only if the caller correctly sets `ENVIRONMENT`. Consider a strict allowlist (`!= "production"` only) or remove the debug response entirely.

**Severity:** Medium — potential token leak in mis-configured deployments.
**Status:** 🔴 Open

---

### CR-S5 — No rate limiting on authentication endpoints

**File:** [`backend/app/api/v1/endpoints/auth.py`](../backend/app/api/v1/endpoints/auth.py)

`POST /auth/login`, `POST /auth/register`, and `POST /auth/password-reset/request` have no rate limiting. Brute-force and credential stuffing are unmitigated. Add `slowapi` middleware with a per-IP limiter.

**Severity:** Medium — active attack surface.
**Status:** 🔴 Open

---

### CR-S6 — `db.commit()` called inside endpoint, bypassing the `get_db` rollback guarantee

**File:** [`backend/app/api/v1/endpoints/admin.py`](../backend/app/api/v1/endpoints/admin.py) — `upload_hierarchy()`

```python
await db.commit()          # explicit commit inside handler
return HierarchyUploadResult(...)
```

The `get_db` dependency commits on clean exit and rolls back on exception. Calling `db.commit()` directly in the handler means any exception raised *after* this commit but *before* `get_db` exits leaves the DB in a partially-committed state without a rollback. Remove the explicit commit and rely on the dependency.

**Severity:** Medium — data integrity risk under error conditions.
**Status:** 🔴 Open

---

### CR-S7 — Concurrent 401 refresh race condition in the Axios interceptor

**File:** [`frontend/src/api/client.ts`](../frontend/src/api/client.ts)

If two requests return 401 simultaneously, both interceptors fire independently and two refresh requests are issued. The second may fail (if backend enforces single-use or issues new tokens that invalidate the first), causing an unexpected logout. A standard fix is to queue pending requests behind a single in-flight refresh promise:

```typescript
let refreshPromise: Promise<string> | null = null
// Interceptor: if refreshPromise exists, await it; else create and assign it
```

**Severity:** Medium — intermittent unexpected logouts.
**Status:** ✅ Resolved (2026-04-13) — Axios interceptor queues concurrent requests behind a single in-flight refresh promise.

---

### CR-S8 — JWT tokens stored in `localStorage` (XSS-accessible)

**File:** [`frontend/src/store/authStore.ts`](../frontend/src/store/authStore.ts)

Zustand `persist` writes `accessToken` and `refreshToken` to `localStorage` under key `auth-storage`. `localStorage` is readable by any JavaScript executing on the page, making tokens vulnerable to XSS. The refresh token in particular should be stored in an `HttpOnly` cookie (requires backend support) or at minimum in `sessionStorage` (cleared on tab close).

**Severity:** Medium — token exfiltration risk via XSS.
**Status:** ✅ Resolved (2026-04-13) — Refresh token moved to an `HttpOnly` `SameSite=Lax` cookie set by the backend; the frontend no longer stores or transmits the refresh token.

---

## 4. Duplicated Logic

### CR-D1 — `selectinload` option chain repeated 3× in `TicketService`

**File:** [`backend/app/services/ticket_service.py`](../backend/app/services/ticket_service.py)

The identical 9-item eager-load chain appears verbatim in `get_by_id()`, `list_all()`, and `list_by_status()`. `UserService` correctly uses a `_user_options()` class method for the same pattern. Extract an equivalent `_ticket_options()` method:

```python
@staticmethod
def _ticket_options() -> list:
    return [
        selectinload(Ticket.organization),
        selectinload(Ticket.creator).selectinload(User.organization),
        selectinload(Ticket.owner).selectinload(User.organization),
        selectinload(Ticket.priority),
        selectinload(Ticket.category),
        selectinload(Ticket.affected_group),
        selectinload(Ticket.attachments),
        selectinload(Ticket.comments)
            .selectinload(Comment.author)
            .selectinload(User.organization),
        selectinload(Ticket.status_logs),
    ]
```

**Status:** 🟠 Open

---

### CR-D2 — `ORG_LEVEL_ABBREV` defined in three places

**Files:**
- [`backend/app/models/models.py`](../backend/app/models/models.py) — Python dict
- [`frontend/src/types/index.ts`](../frontend/src/types/index.ts) — TS const
- [`mobile/src/types/index.ts`](../mobile/src/types/index.ts) — TS const (no mapping present but levels duplicated)

These must be kept in sync manually. Consider deriving the mapping from a `/organizations/levels` API endpoint, or at minimum adding a comment cross-referencing the other definitions.

**Status:** 🟠 Open

---

### CR-D3 — SQLAlchemy `Enum` boilerplate repeated 7×

**File:** [`backend/app/models/models.py`](../backend/app/models/models.py)

```python
# Appears 7 times:
Enum(SomeEnum, values_callable=lambda e: [x.value for x in e], create_constraint=False)
```

Extract a helper:

```python
def pg_enum(enum_cls: type) -> Enum:
    return Enum(enum_cls, values_callable=lambda e: [x.value for x in e], create_constraint=False)
```

**Status:** 🟠 Open

---

### CR-D4 — `STATUS_COLORS` / `STATUS_LABELS` duplicated across web and mobile

**Files:**
- [`frontend/src/components/board/KanbanBoard.tsx`](../frontend/src/components/board/KanbanBoard.tsx)
- [`mobile/src/screens/TicketListScreen.tsx`](../mobile/src/screens/TicketListScreen.tsx)

Same constant defined independently in both clients. If a new status is added, it must be updated in both.

**Status:** 🟠 Open

---

### CR-D5 — Two separate "list all users" endpoints

**Files:**
- `GET /users/` in [`backend/app/api/v1/endpoints/users.py`](../backend/app/api/v1/endpoints/users.py) — superuser only
- `GET /admin/users` in [`backend/app/api/v1/endpoints/admin.py`](../backend/app/api/v1/endpoints/admin.py) — admin group

Both call `service.list_all()` and return `list[UserResponse]`. The only difference is the auth guard. Unify into one endpoint with a shared auth guard that accepts both `admin` group and superuser.

**Status:** 🟠 Open

---

### CR-D6 — `canCloseTicket` checked by name in frontend, by permission in backend

**Files:**
- [`frontend/src/components/tickets/TicketDetail.tsx`](../frontend/src/components/tickets/TicketDetail.tsx) — `user?.groups?.includes('schirrmeister')`
- [`backend/app/api/v1/endpoints/tickets.py`](../backend/app/api/v1/endpoints/tickets.py) — `user_has_permission(..., "close_ticket")`

Currently these are equivalent because `schirrmeister` holds `close_ticket`. However, if that permission is reassigned via the admin panel, the frontend check becomes stale. The frontend should query user permissions from the `GET /auth/me` response rather than hard-coding group names.

**Status:** 🟠 Open

---

## 5. Missing Error Handling

### CR-E1 — No React Error Boundary

**File:** [`frontend/src/App.tsx`](../frontend/src/App.tsx)

An unhandled render-time error in any component shows a blank white screen with no explanation. Wrap the app root in an `<ErrorBoundary>`:

```tsx
<ErrorBoundary fallback={<p>Something went wrong. Please reload.</p>}>
  <AppInner />
</ErrorBoundary>
```

**Status:** 🟡 Open

---

### CR-E2 — `add_comment` returns a comment without the `author` relation loaded

**File:** [`backend/app/services/ticket_service.py`](../backend/app/services/ticket_service.py) — `add_comment()`

```python
await self.db.refresh(comment)
return comment   # comment.author is not eagerly loaded
```

`CommentResponse` accesses `comment.author`. In `asyncpg` async context, accessing a lazy-loaded relation raises `sqlalchemy.exc.MissingGreenlet`. The fix is to re-query the comment with the author eagerly loaded after the insert.

**Status:** 🔴 Open (may be causing silent serialisation errors)

---

### CR-E3 — `assert` used as runtime guard in production code

**File:** [`backend/app/services/user_service.py`](../backend/app/services/user_service.py)

```python
assert refreshed is not None
```

Running Python with `-O` (optimize flag) strips `assert` statements. Replace with explicit raises:

```python
if refreshed is None:
    raise RuntimeError(f"User {user.id} disappeared after creation")
```

**Status:** 🟡 Open

---

### CR-E4 — `organization_id` FK not validated at service layer

**Files:** [`backend/app/services/user_service.py`](../backend/app/services/user_service.py), [`backend/app/api/v1/endpoints/auth.py`](../backend/app/api/v1/endpoints/auth.py)

Passing a non-existent `organization_id` results in a Postgres `IntegrityError` that surfaces as an unhandled 500. The service should query the org first and raise `NotFoundException` / `ValidationException` with a descriptive message.

**Status:** 🟡 Open

---

### CR-E5 — Mobile silent logout after token refresh failure

**File:** [`mobile/src/api/index.ts`](../mobile/src/api/index.ts)

After deleting SecureStore tokens on refresh failure, no state update or screen navigation occurs. The user stays on the current screen with stale UI until the next API call error. The fix requires either a simple event bus or a Zustand store to trigger a navigation-to-login.

**Status:** 🟡 Open

---

## 6. Large Module Detail: Split Candidates

### AdminPanel.tsx (1 029 lines) — 🔴 Split urgently

`AdminPanel.tsx` contains 9 independently functional sub-components inlined inside a single file. Each sub-component owns its own state, API calls, and JSX (100–160 lines each). None of them share state with each other — they are only co-located by tab index.

**Recommended split:**

```
frontend/src/components/admin/
  AdminPanel.tsx          ← tabs shell only (~60 lines)
  PrioritiesAdmin.tsx     ← replaces inline PrioritiesCategoriesAdmin (for priorities)
  CategoriesAdmin.tsx     ← replaces inline PrioritiesCategoriesAdmin (for categories)
  GroupsAdmin.tsx         ← replaces inline GroupsAdmin
  UserRoleAdmin.tsx       ← replaces inline UserRoleAdmin
  RolePermissionsAdmin.tsx← replaces inline RolePermissionsAdmin
  AgeThresholdsAdmin.tsx  ← replaces inline AgeThresholdsAdmin
  UsersAdmin.tsx          ← replaces inline UsersAdmin
  EmailConfigAdmin.tsx    ← replaces inline EmailConfigAdmin
  BulkUploadAdmin.tsx     ← replaces inline BulkUploadAdmin + HierarchyUploadAdmin
```

**Status:** 🔴 Open

---

### TicketDetail.tsx (507 lines) — ⚠ Split candidate

`TicketDetail` handles ticket field editing, status transitions, waiting-for notes, assignee/priority/category selectors, comment thread (add/edit/delete), attachment gallery (upload/delete), and status history in one component function. It has a single 350-line `return` JSX block.

**Recommended split:**

```
frontend/src/components/tickets/
  TicketDetail.tsx            ← orchestrator, state & callbacks (~100 lines)
  TicketMetaPanel.tsx         ← assignee, priority, category, group selectors
  TicketComments.tsx          ← comment list + add form
  TicketAttachments.tsx       ← attachment gallery + upload
  TicketStatusHistory.tsx     ← status log timeline
```

**Status:** 🟠 Open

---

### admin.py (641 lines) — ⚠ Backend split candidate

`admin.py` conflates three distinct access levels and mixes business logic into endpoint handlers. The XLSX parsing and DB writes in `bulk_upload_users()` and `upload_hierarchy()` (each ~75–80 lines) should be extracted to `BulkUploadService` / `HierarchyService`.

**Recommended split:**

```
backend/app/api/v1/endpoints/
  admin_config.py      ← config items, app settings
  admin_groups.py      ← user groups, permissions, role-permissions
  admin_users.py       ← admin user list, bulk upload
  admin_email.py       ← email configs
  admin_hierarchy.py   ← hierarchy import

backend/app/services/
  bulk_service.py      ← bulk_upload_users(), import_hierarchy() logic
```

**Status:** 🟠 Open

---

## 7. Inconsistent Patterns

### CR-P1 — Stray mid-file import in `schemas/ticket.py`

**File:** [`backend/app/schemas/ticket.py`](../backend/app/schemas/ticket.py)

```python
# ❌ Mid-file import (PEP 8 violation)
from app.models.models import TicketStatus
```

All imports must be at the top of the file.

**Status:** 🟡 Open

---

### CR-P2 — `get_unrestricted_user` alias for a private function

**File:** [`backend/app/core/deps.py`](../backend/app/core/deps.py)

```python
get_unrestricted_user = _get_user_base
```

`_get_user_base` has a leading underscore (private by convention) but is exported via a public alias. Rename `_get_user_base` to `get_unrestricted_user` directly.

**Status:** 🟡 Open

---

### CR-P3 — BFS uses `list.pop(0)` instead of `deque.popleft()`

**File:** [`backend/app/services/organization_service.py`](../backend/app/services/organization_service.py)

```python
queue = [org_id]
while queue:
    current = queue.pop(0)   # O(n) — use deque.popleft() instead
```

**Status:** 🟡 Open

---

### CR-P4 — `_ensure_age_defaults` issues N individual SELECT queries

**File:** [`backend/app/api/v1/endpoints/admin.py`](../backend/app/api/v1/endpoints/admin.py)

One `SELECT` per threshold key (currently 5) on every call to `GET /admin/app-settings`. Replace with a single `WHERE key IN (...)` query.

**Status:** 🟡 Open

---

### CR-P5 — Kanban board filters by user name string instead of user ID

**File:** [`frontend/src/components/board/KanbanBoard.tsx`](../frontend/src/components/board/KanbanBoard.tsx)

```typescript
const creatorOk = !filterCreator || t.creator_name === filterCreator
```

Name-based filtering breaks when two users share a name, or when a user's name is changed. Filter by `creator_id` / `assignee_id` (UUIDs) instead.

**Status:** 🟡 Open

---

### CR-P6 — Priority CSS class mapping hardcodes German names

**File:** [`frontend/src/components/board/TicketCard.tsx`](../frontend/src/components/board/TicketCard.tsx)

```typescript
const PRIORITY_CLASS: Record<string, string> = {
  Kritisch: 'priority-critical',
  Hoch: 'priority-high',
  ...
}
```

Priorities are user-configurable `ConfigItem` values in the database. If an admin renames "Kritisch" to "Critical", the colour coding silently breaks. Decouple the visual class from the name — use a `sort_order` or a dedicated `severity` attribute instead.

**Status:** 🟡 Open

---

### CR-P7 — Destructive actions use `window.confirm()`

**File:** [`frontend/src/components/tickets/TicketDetail.tsx`](../frontend/src/components/tickets/TicketDetail.tsx)

Native `window.confirm()` is non-styleable, blocked in some browser sandboxes, and poor UX. Replace with an inline confirmation button / modal.

**Status:** 🟡 Open

---

### CR-P8 — Mobile `TicketSummary` type uses `owner_id` instead of `assignee_id`

**File:** [`mobile/src/types/index.ts`](../mobile/src/types/index.ts)

The backend `TicketSummary` schema renames `owner_id` → `assignee_id` via `populate_names`. The mobile type still declares `owner_id`, so `ticket.assignee_id` is always `undefined` in mobile code — this is a silent data bug.

**Status:** 🔴 Open

---

### CR-P9 — `mobile/app.json` contains placeholder values

**File:** [`mobile/app.json`](../mobile/app.json)

```json
"bundleIdentifier": "com.yourcompany.ticketsystem",
"projectId": "your-eas-project-id"
```

These must be replaced before any Expo/EAS build. No tooling or CI check prevents shipping placeholder values.

**Status:** 🟡 Open

---

## 8. Issue Summary

### By Severity

| Severity | ID | Title |
|----------|----|-------|
| 🔴 Critical / Security | CR-S1 | Synchronous file write in async endpoint |
| 🔴 Critical / Security | CR-S2 | Avatar delete path not validated |
| 🔴 Critical / Security | CR-S3 | SMTP password stored plain text |
| 🔴 Critical / Security | CR-S4 | Reset token returned in response body |
| 🔴 Critical / Security | CR-S5 | No rate limiting on auth endpoints |
| 🔴 Critical / Security | CR-S6 | `db.commit()` inside endpoint bypasses rollback |
| 🔴 Security | CR-S7 | Concurrent 401 refresh race condition | ✅ Resolved |
| 🔴 Security | CR-S8 | JWT tokens in `localStorage` | ✅ Resolved |
| 🔴 Bug | CR-E2 | `add_comment` missing `author` eager load |
| 🔴 Bug | CR-P8 | Mobile `TicketSummary` uses `owner_id` not `assignee_id` |
| 🟠 Duplication | CR-D1 | `selectinload` chain repeated 3× |
| 🟠 Duplication | CR-D2 | `ORG_LEVEL_ABBREV` in 3 places |
| 🟠 Duplication | CR-D3 | SQLAlchemy `Enum` boilerplate repeated 7× |
| 🟠 Duplication | CR-D4 | `STATUS_COLORS`/`STATUS_LABELS` in web + mobile |
| 🟠 Duplication | CR-D5 | Two separate "list all users" endpoints |
| 🟠 Duplication | CR-D6 | `canCloseTicket` checked by name vs. permission |
| 🟠 Size | Large-1 | `AdminPanel.tsx` 1 029 lines — split urgently |
| 🟠 Size | Large-2 | `TicketDetail.tsx` 507 lines — split candidate |
| 🟠 Size | Large-3 | `admin.py` 641 lines — split candidate |
| 🟡 Error handling | CR-E1 | No React Error Boundary |
| 🟡 Error handling | CR-E3 | `assert` used as runtime guard |
| 🟡 Error handling | CR-E4 | `organization_id` FK not validated at service layer |
| 🟡 Error handling | CR-E5 | Mobile silent logout after refresh failure |
| 🟡 Inconsistency | CR-P1 | Stray mid-file import in `schemas/ticket.py` |
| 🟡 Inconsistency | CR-P2 | `get_unrestricted_user` alias for private function |
| 🟡 Inconsistency | CR-P3 | BFS uses `list.pop(0)` not `deque` |
| 🟡 Inconsistency | CR-P4 | N individual queries in `_ensure_age_defaults` |
| 🟡 Inconsistency | CR-P5 | Filter by user name string, not ID |
| 🟡 Inconsistency | CR-P6 | Priority CSS class hardcodes German names |
| 🟡 Inconsistency | CR-P7 | `window.confirm()` for destructive actions |
| 🟡 Inconsistency | CR-P9 | `app.json` placeholder values |

### Counts

| Category | Count |
|----------|-------|
| 🔴 Security / correctness bugs | 10 |
| 🟠 Duplication + large modules | 9 |
| 🟡 Error handling + inconsistency | 11 |
| **Total** | **30** |

---

## 9. Progress Tracker

### 2026-04-06 — Baseline (all 30 issues open)

No issues resolved yet. This is the initial review establishing the baseline.

**Highest-priority work:**

1. Fix CR-E2 (`add_comment` missing eager load) — likely causing live bugs
2. Fix CR-P8 (mobile `owner_id`/`assignee_id` mismatch) — data always wrong
3. Fix CR-S1 (sync I/O in async context) — event-loop blocking
4. Split `AdminPanel.tsx` (Large-1) — developer experience severely degraded
5. Add rate limiting CR-S5 before any public deployment

---

### 2026-04-13 — Security Hardening

**Resolved since baseline:**

| ID | Fix |
|----|-----|
| CR-S7 | Axios interceptor queues concurrent 401s behind a single in-flight refresh promise |
| CR-S8 | Refresh token moved to `HttpOnly` `SameSite=Lax` cookie by the backend |

**Newly identified (IMAP ingestion pipeline — all fixed in the same session):**

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| IMAP-1 | No IMAP connection timeout — hung server pins thread-pool worker | High | ✅ Fixed |
| IMAP-2 | No raw message size limit before parsing — DoS / OOM risk | High | ✅ Fixed |
| IMAP-3 | No MIME part count limit — MIME-bomb amplification | High | ✅ Fixed |
| IMAP-4 | Org-scope bypass — registered user in org A could comment on org B tickets | High | ✅ Fixed |
| IMAP-5 | Comment body not length-capped — newsletter emails bloat DB | Medium | ✅ Fixed |
| IMAP-6 | Attachment filename not length-capped — exceeds VARCHAR(255) | Medium | ✅ Fixed |
| IMAP-7 | `_BARE_RE` subject pattern too broad — false-positive matching | Medium | ✅ Fixed |
| IMAP-8 | `sender_prefix` added to all comments including known users | Low | ✅ Fixed |
| IMAP-9 | `_mark_seen` inside DB transaction — network blip causes duplicate comment | Medium | ✅ Fixed |
| IMAP-10 | `IMAP_USE_SSL=False` not blocked in production | Medium | ✅ Fixed |

**Open count after this pass: 28 (was 30 at baseline)**

---

## 10. Recommendations

### Immediate (fix before next release)

1. **CR-E2** — Re-query the comment with `author` join after insert in `add_comment()`.
2. **CR-P8** — Fix mobile `TicketSummary` type: rename `owner_id` → `assignee_id`.
3. **CR-S1** — Replace `open()` with `aiofiles.open()` in avatar upload handler.
4. **CR-S6** — Remove explicit `await db.commit()` from `upload_hierarchy()`; rely on `get_db`.

### Short-term (next sprint)

5. **CR-S5** — Add `slowapi` rate limiting to all auth endpoints.
6. **Large-1** — Split `AdminPanel.tsx` into ~10 focused components.
7. **CR-D1** — Extract `_ticket_options()` in `TicketService`.
8. **CR-E1** — Add a top-level React `<ErrorBoundary>`.
9. **CR-P1** — Move stray import to top of `schemas/ticket.py`.
10. **CR-P2** — Rename `_get_user_base` → `get_unrestricted_user` directly.

### Medium-term

11. **CR-S3** — Encrypt SMTP passwords at rest with Fernet.
12. **CR-S4** — Tighten reset token guard or remove dev-mode response.
13. **Large-2** — Split `TicketDetail.tsx` into ~5 sub-components.
14. **Large-3** — Split `admin.py` and extract `BulkUploadService`.
15. **CR-D5** — Unify the two "list users" endpoints.
16. **CR-P6** — Decouple priority colour from priority name (use `sort_order`).

### Long-term

17. **CR-S7** — Queue concurrent refresh requests behind a single promise.
18. **CR-S8** — Move refresh token to `HttpOnly` cookie.
19. **CR-D6** — Drive frontend permission checks from `user.permissions` API data.
20. **CR-P3** — Switch BFS queue to `collections.deque`.
