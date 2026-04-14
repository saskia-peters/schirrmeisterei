"""Outgoing email notifications for ticket watchers.

Sends status-change emails to all watchers of a ticket using the ticket
organisation's SMTP configuration.  Plain stdlib smtplib runs inside
asyncio.to_thread so the event loop is never blocked.

Errors are logged and silently swallowed — a failed SMTP delivery must never
cause a ticket-status update to be rolled back.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


async def send_watcher_notifications(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    use_tls: bool,
    to_addresses: list[str],
    ticket_number: int,
    ticket_title: str,
    old_status: str,
    new_status: str,
) -> None:
    """Send a status-change notification e-mail to each watcher address.

    Runs the blocking smtplib call in a thread pool so the async event loop
    is not blocked.  All exceptions are caught and logged — callers should
    fire this as a background task (asyncio.create_task) and not await it.
    """
    if not to_addresses:
        return

    subject = f"[Ticket #{ticket_number}] Status changed: {old_status} → {new_status}"
    body_text = (
        f"Ticket #{ticket_number}: {ticket_title}\n\n"
        f"The status has changed from '{old_status}' to '{new_status}'.\n"
    )

    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(to_addresses)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        try:
            conn = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if use_tls:
                conn.starttls()
            if smtp_user and smtp_password:
                conn.login(smtp_user, smtp_password)
            conn.sendmail(from_email, to_addresses, msg.as_string())
            conn.quit()
            logger.info(
                "watcher-email: sent ticket #%d notification to %d recipient(s)",
                ticket_number,
                len(to_addresses),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "watcher-email: failed to send notification for ticket #%d: %s",
                ticket_number,
                exc,
            )

    try:
        await asyncio.to_thread(_send)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "watcher-email: unexpected error for ticket #%d: %s",
            ticket_number,
            exc,
        )
