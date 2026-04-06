# API Reference

Interactive documentation is available at runtime:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/openapi.json`

## Base URL

```
/api/v1
```

## Authentication

All endpoints (except `/auth/login`, `/auth/register`, `/auth/refresh`) require a JWT Bearer token:

```http
Authorization: Bearer <access_token>
```

---

## Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Obtain access + refresh tokens |
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/refresh` | Exchange refresh token for new pair |
| `GET` | `/auth/me` | Get current user profile |
| `POST` | `/auth/totp/setup` | Generate TOTP secret + QR code |
| `POST` | `/auth/totp/verify` | Verify OTP code and enable 2FA |
| `DELETE` | `/auth/totp/disable` | Disable 2FA (requires current OTP code) |
| `POST` | `/auth/password-reset/request` | Request a password-reset token (superusers only) |
| `POST` | `/auth/password-reset/confirm` | Set a new password using the reset token |

### Login request

```json
{
  "email": "alice@example.com",
  "password": "hunter2"
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Ticket Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tickets/board` | Kanban board (all tickets grouped by status) |
| `GET` | `/tickets/` | List tickets (filtered by org visibility) |
| `POST` | `/tickets/` | Create a ticket |
| `GET` | `/tickets/{id}` | Get ticket detail |
| `PATCH` | `/tickets/{id}` | Update ticket fields |
| `DELETE` | `/tickets/{id}` | Delete ticket (creator or superuser only) |
| `PATCH` | `/tickets/{id}/status` | Change ticket status |
| `PATCH` | `/tickets/{id}/waiting-for` | Edit the waiting-for reason |
| `POST` | `/tickets/{id}/attachments` | Upload an image attachment |
| `DELETE` | `/tickets/{id}/attachments/{att_id}` | Delete an attachment |
| `POST` | `/tickets/{id}/comments` | Add a comment |
| `PATCH` | `/tickets/{id}/comments/{cmt_id}` | Edit a comment |
| `DELETE` | `/tickets/{id}/comments/{cmt_id}` | Delete a comment |
| `GET` | `/tickets/{id}/status-log` | Full status-change history |

---

## Admin Endpoints

Requires `admin` group or `is_superuser=true`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | List all users (with groups) |
| `GET` | `/admin/users/{id}/groups` | Get a user's group names |
| `PUT` | `/admin/users/{id}/groups` | Replace a user's group memberships |
| `GET/POST/PATCH/DELETE` | `/admin/config-items` | Manage priorities, categories, affected groups |
| `GET/POST/PATCH/DELETE` | `/admin/user-groups` | Manage role definitions |
| `GET` | `/admin/user-groups-detail` | User groups with their permissions |
| `PUT` | `/admin/user-groups/{id}/permissions` | Replace permissions for a role |
| `GET` | `/admin/permissions` | List all available permissions |
| `GET/PATCH` | `/admin/app-settings` | Read / update application settings (e.g. age thresholds) |
| `GET/POST/PATCH` | `/admin/email-configs` | SMTP configuration per organisation |
| `POST` | `/admin/users/bulk-upload` | Import users from XLSX |
| `POST` | `/admin/hierarchy/upload` | Import organisation hierarchy from XLSX |

### Hierarchy XLSX format

The XLSX must have columns:

| Column | Values | Notes |
|--------|--------|-------|
| `level` | `ortsverband`, `regionalstelle`, `landesverband`, `leitung` | Exact string |
| `name` | Any string | Organisation name |
| `parent_name` | Any string (optional) | Name of the parent organisation |

Existing organisations (same name + level) are **skipped** automatically.

---

## Organisation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/organisations/` | List all organisations |
| `GET` | `/organisations/landesverbaende` | List Landesverbände |
| `GET` | `/organisations/regionalstellen` | List Regionalstellen (optionally filter by `landesverband_id`) |
| `GET` | `/organisations/ortsverbaende` | List Ortsverbände (optionally filter by `regionalstelle_id`) |

## User Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users/assignable` | Lightweight user list for assignee selectors |
| `GET` | `/users/` | List all users (superuser only) |
| `POST` | `/users/` | Create a user (superuser only) |
| `GET` | `/users/{id}` | Get user by ID |
| `PATCH` | `/users/{id}` | Update user (self or superuser) |
