# User Guide

## Logging In

1. Open the TicketSystem URL in your browser.
2. Enter your **email** and **password**.
3. If Two-Factor Authentication (2FA) is enabled for your account, enter the 6-digit code from your authenticator app.

## The Kanban Board

After login you land on the **Kanban board**. Tickets are organised in columns:

| Column | Meaning |
|--------|---------|
| New | Just created, not yet started |
| In Progress | Actively being worked on |
| Waiting | Blocked or awaiting external response |
| Resolved | Issue fixed, pending confirmation |
| Closed | Completed and archived |

**Drag and drop** a ticket card to move it to another status column.

Click a ticket title to open its **detail view** where you can edit fields, add comments, and change the assignee.

## Navbar Colour

The navbar background colour indicates your organisational level at a glance:

| Colour | Level |
|--------|-------|
| Light blue | Ortsverband |
| Light orange | Regionalstelle |
| Light green | Landesverband |
| Light red | Leitung |

## Creating a Ticket

1. Click **+ New Ticket** on the board.
2. Fill in the title and description (both required).
3. Optionally set Priority, Category, Affected Group, and Assignee.
4. Click **Create Ticket**.

## Filtering Tickets

Use the filter bar above the board to narrow tickets by:

- Status
- Priority
- Category
- Assignee
- Date range

## My Profile

Click your name in the top-right corner to access:

- **Change password**
- **Enable / disable 2FA (TOTP)**

---

## Admin Panel

Users in the **admin** group or with superuser status can access the Admin Panel via the ⚙ button in the navbar.

### Tabs

| Tab | Purpose |
|-----|---------|
| Priorities | Manage priority labels (e.g. Critical, High, Medium) |
| Categories | Manage category labels |
| Affected Groups | Manage affected-group labels |
| User Roles | Create and rename user groups/roles |
| Role Permissions | Assign fine-grained permissions to roles |
| Age Thresholds | Configure ticket-age warning thresholds |
| Users | View all users; change their roles and activation status |
| Email Config | Configure SMTP settings per organisation |
| Bulk Upload | Import users from an XLSX file |
| Hierarchy Import | Import the organisation hierarchy from an XLSX file |

### Importing the Organisation Hierarchy

Prepare an XLSX file with three columns:

| level | name | parent_name |
|-------|------|-------------|
| `leitung` | Bundesleitung | |
| `landesverband` | LV Bayern | Bundesleitung |
| `regionalstelle` | Rst München | LV Bayern |
| `ortsverband` | OV Schwabing | Rst München |

- `level` must be one of: `ortsverband`, `regionalstelle`, `landesverband`, `leitung`
- `parent_name` is optional for the top-level node
- Organisations that already exist (same name + level) are **skipped**

### Bulk User Import

Prepare an XLSX file with columns:

| email | full_name | password | organization_id (optional) |
|-------|-----------|----------|---------------------------|
| alice@example.com | Alice Smith | Secret1! | |

If `organization_id` is omitted, users are assigned to your own organisation.
