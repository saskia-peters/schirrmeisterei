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
2. Fill in the **title** and **description** (required).
3. Optionally attach one or more files — **images or PDFs** are supported (max 10 MB each).
4. Optionally set Priority, Category, Affected Group, and Assignee.
5. Click **Create Ticket**.

!!! tip "Mobile"
    On small screens the optional fields (Priority, Category, Affected Group, Assignee) are hidden by default to keep the form compact. The form still works with just title and description.

## Attaching Files to a Ticket

Both **images** (JPEG, PNG, GIF, WebP) and **PDF documents** can be attached to a ticket:

- During ticket creation — use the file picker in the create form.
- After creation — open the ticket detail view and use the attachment upload button.

Each file is validated against its actual content (not just the extension) and must not exceed 10 MB.

---

## Sending an Email to a Ticket

When IMAP ingestion is enabled by your administrator, you can reply to a ticket by email.

**Subject line format** — include the ticket reference in square brackets:

```
[Ticket #42] Follow-up question about the power outage
[Ticket-42] Follow-up question
[Ticket 42] Follow-up question
```

The email body is added as a comment on the ticket.  Attached images and PDFs are saved as ticket attachments automatically.

**Rules:**

- Your **From:** address must match a registered, active user account.
- You may only comment on tickets that belong to your own organisation.
- Superusers may comment on any ticket.
- Messages from unrecognised senders are silently discarded (configurable — see admin settings).

---

---

## Watching a Ticket

Any user who can see a ticket can **watch** it to receive email notifications when its status changes.

### Subscribe / unsubscribe

1. Open the ticket detail view by clicking its title.
2. Click the **🔔 Watch** button in the top-right area of the ticket header to subscribe.
3. Click **🔕 Unwatch** to stop receiving notifications.

The button label and style reflect your current watch state at a glance.

### When are notifications sent?

An email is sent to all watchers (except the user who performed the status change) whenever a ticket's status is updated.

**Requirements for notifications:**

- Your organisation must have an outgoing SMTP configuration set up in the Admin Panel → *Email Config* tab.
- Your user account must have a valid email address.
- You must be watching the ticket at the time of the status change.

The notification email includes the ticket number, title, old status, and new status.

!!! note
    If no Email Config exists for the ticket's organisation, notifications are silently skipped. Contact your administrator to enable outgoing email.

---

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
| Email Ingestion | Manually trigger an IMAP poll cycle and review results |
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
