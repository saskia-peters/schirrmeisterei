# Architecture

## Overview

TicketSystem is a three-tier application:

```
Browser / Mobile
      │
      ▼
┌─────────────────────┐
│  React SPA          │  Vite + TypeScript 5
│  (frontend/)        │  React Query · Zustand · dnd-kit
└────────┬────────────┘
         │ HTTPS / REST
         ▼
┌─────────────────────┐
│  FastAPI backend    │  Python 3.13 + uvicorn
│  (backend/)         │  SQLAlchemy async · Alembic
└────────┬────────────┘
         │ asyncpg
         ▼
┌─────────────────────┐
│  PostgreSQL 18      │  schema: ticketsystem
└─────────────────────┘
```

## Organisation Hierarchy

Organisations form a strict 4-level tree:

```
Leitung (LTG)
  └── Landesverband (LV)
        └── Regionalstelle (Rst)
              └── Ortsverband (OV)
```

Users belong to exactly one organisation node.
**Visibility rules:**

| Level | Sees |
|-------|------|
| Leitung | All tickets in the entire system |
| Landesverband | All tickets within its LV subtree |
| Regionalstelle | All tickets within its Rst subtree |
| Ortsverband | Only tickets created by its OV members |

The `OrganizationService.get_visible_org_ids()` method implements these rules.

## Data Model (key tables)

```
organisations          users
  id (UUID)              id (UUID)
  level (enum)           email
  name                   hashed_password
  parent_id (FK self)    organization_id (FK)
                         is_superuser

tickets                ticket_watchers
  id (UUID)              ticket_id (FK, PK)
  title                  user_id  (FK, PK)
  description
  status (enum)        user_group_memberships
  creator_id (FK)        user_id (FK)
  assignee_id (FK)       group_id (FK)
  organization_id (FK)
  priority_id (FK)     user_groups
  category_id (FK)       id (UUID)
  affected_group_id (FK) name
```

## Authentication Flow

1. `POST /api/v1/auth/login` → returns `access_token` (15 min) in the JSON body and sets the `refresh_token` (7 days) as an **HttpOnly cookie** (not accessible to JavaScript)
2. All protected endpoints require `Authorization: Bearer <access_token>`
3. `POST /api/v1/auth/refresh` reads the HttpOnly cookie and returns a new access token
4. Optional TOTP: user enables 2FA; subsequent logins require OTP code

## Background Services

The backend runs optional background asyncio tasks started inside the FastAPI lifespan:

| Service | Config flag | Purpose |
|---------|-------------|--------|
| IMAP poller (`imap_poller.py`) | `IMAP_ENABLED=true` | Polls a mailbox for UNSEEN messages, parses `[Ticket #N]` subjects, and adds comments + attachments |

The IMAP poller runs as a single `asyncio.Task` (no separate worker process or queue). IMAP I/O is dispatched to the default `ThreadPoolExecutor` via `run_in_executor` so the event loop is never blocked.

## Ticket Watchers & Email Notifications

Any user who can see a ticket can subscribe as a **watcher** (`ticket_watchers` join table, composite PK `(ticket_id, user_id)`).

When `TicketService.update_status()` detects a real status change it calls `_schedule_watcher_notifications()`, which:

1. Queries the org's `EmailConfig` (SMTP credentials, encrypted at rest with Fernet).
2. Filters out the user who triggered the change.
3. Fires an `asyncio.create_task()` wrapping `email_service.send_watcher_notifications()`.

Using `create_task()` (fire-and-forget) means SMTP latency or failure **never blocks** the API response.

`send_watcher_notifications()` (`backend/app/services/email_service.py`) runs `smtplib` inside `asyncio.to_thread()` to keep the event loop free. All SMTP exceptions are caught and logged — they are never re-raised to the caller.

New API surface:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/tickets/{id}/watch` | Subscribe current user |
| `DELETE` | `/api/v1/tickets/{id}/watch` | Unsubscribe current user |

`TicketResponse` gains a `watcher_ids: list[str]` field populated on serialisation.

## Navbar Colour Coding

The navbar background changes colour depending on the logged-in user's organisation level:

| Level | Colour |
|-------|--------|
| Ortsverband | Light blue `#dbeafe` |
| Regionalstelle | Light orange `#fed7aa` |
| Landesverband | Light green `#dcfce7` |
| Leitung | Light red `#fee2e2` |
