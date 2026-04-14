# TicketSystem Documentation

Welcome to the **TicketSystem** documentation — a multi-tenant support-ticket platform for hierarchical organisations (Leitung → Landesverband → Regionalstelle → Ortsverband).

## Quick Start

```bash
# Clone the repo and start the dev stack
just dev-up

# Reset and seed the database
just db-reset
```

## Features

- **Role-based access control** — Helfende, Schirrmeister, Admin role hierarchy
- **Multi-tenancy** — Tickets are scoped to organisational units; higher levels see aggregate views
- **Kanban board** — Drag-and-drop ticket management with real-time status updates
- **File attachments** — Upload images and PDFs directly to tickets and comments
- **Email-to-ticket ingestion** — Incoming emails with `[Ticket #N]` in the subject are automatically added as comments (with attachments) via IMAP polling
- **Bulk operations** — Import users and organisation hierarchies from XLSX
- **2FA / TOTP** — Optional time-based one-time password authentication
- **Email notifications** — Per-organisation SMTP configuration
- **REST API** — Fully documented OpenAPI 3.1 spec at `/api/docs`
- **Hardened security** — HttpOnly refresh-token cookies, Fernet-encrypted SMTP credentials, CORS origin validator, IMAP input sanitisation

## Navigation

| Section | What's inside |
|---------|---------------|
| [Architecture](architecture.md) | System design, data model, org hierarchy |
| [API Reference](api.md) | Endpoint catalogue, authentication flow |
| [Deployment](deployment.md) | Docker/Podman, environment variables, GitHub Pages |
| [Development Guide](development.md) | Local setup, testing, migrations |
| [User Guide](user-guide.md) | Day-to-day usage for end users |
