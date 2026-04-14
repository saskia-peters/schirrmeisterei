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

tickets                user_group_memberships
  id (UUID)              user_id (FK)
  title                  group_id (FK)
  description
  status (enum)        user_groups
  creator_id (FK)        id (UUID)
  assignee_id (FK)       name
  organization_id (FK)
  priority_id (FK)     permissions / role_permissions
  category_id (FK)       (RBAC permission table)
  affected_group_id (FK)
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

## Navbar Colour Coding

The navbar background changes colour depending on the logged-in user's organisation level:

| Level | Colour |
|-------|--------|
| Ortsverband | Light blue `#dbeafe` |
| Regionalstelle | Light orange `#fed7aa` |
| Landesverband | Light green `#dcfce7` |
| Leitung | Light red `#fee2e2` |
