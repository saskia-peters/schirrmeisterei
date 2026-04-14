"""Email-to-ticket ingestion service.

Parses an RFC 2822 email message and, when the subject contains a recognised
ticket reference, appends:
  1. The plain-text (or de-HTMLed) body as a Comment.
  2. Any image or PDF MIME parts as Attachments.

Subject formats recognised (case-insensitive):
  [Ticket #123]   ← canonical — used when sending reply-subject headers
  [Ticket-123]
  [Ticket 123]

Only bracket notation is matched.  Bare-word patterns such as "Ticket 5 …"
are intentionally rejected to avoid false positives from unrelated emails.

Ticket references are matched against the **ticket_number** integer sequence
(the short human-readable number), not the internal UUID.

Comment authorship:
  1. A registered, active user whose ``email`` matches the From: address.
  2. If ``IMAP_REQUIRE_REGISTERED_SENDER=true`` (default): message is rejected.
  3. If ``IMAP_REQUIRE_REGISTERED_SENDER=false``: falls back to the user
     configured via ``IMAP_SYSTEM_USER_EMAIL`` (no superuser fallback).

If no author can be resolved the message is skipped with a warning log.

Org-scope enforcement:
  Non-superuser senders may only post comments on tickets that belong to their
  own organisation.  Superusers may comment on any ticket regardless of org.
"""

from __future__ import annotations

import email as email_lib
import logging
import re
from email.message import Message
from html.parser import HTMLParser

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Comment, Ticket, User
from app.services.ticket_service import TicketService

logger = logging.getLogger(__name__)

# ── subject patterns ──────────────────────────────────────────────────────────

# Bracket notation only: [Ticket #123] / [Ticket-123] / [Ticket 123]
# Deliberate choice: bare-word patterns ("Ticket 5 …") produce too many false
# positives from unrelated emails (e.g. "only ticket 5 items remain").
# Use the canonical [Ticket #N] format in automated reply subjects.
_BRACKET_RE = re.compile(r"\[ticket[\s#\-]*(\d+)\]", re.IGNORECASE)


def parse_ticket_number(subject: str) -> int | None:
    """Return the ticket_number embedded in *subject*, or ``None``."""
    m = _BRACKET_RE.search(subject)
    return int(m.group(1)) if m else None


# ── body extraction ───────────────────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    """Minimal HTML-to-text converter used when no text/plain part exists."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


_MAX_MIME_PARTS = 50     # guard against MIME-bomb / deeply nested multipart messages
_MAX_COMMENT_LENGTH = 50_000  # chars — prevents enormous email bodies bloating the DB


def extract_text_body(msg: Message) -> str:
    """Return the best plain-text representation of *msg*'s body."""
    text_plain = ""
    text_html = ""

    parts = msg.walk() if msg.is_multipart() else [msg]
    for _count, part in enumerate(parts):
        if _count >= _MAX_MIME_PARTS:
            logger.warning("email-ingestion: MIME part limit (%d) reached — truncating body extraction", _MAX_MIME_PARTS)
            break
        ct = part.get_content_type()
        disp = part.get_content_disposition() or ""
        if "attachment" in disp:
            continue
        if ct == "text/plain" and not text_plain:
            raw = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            if raw:
                text_plain = raw.decode(charset, errors="replace")
        elif ct == "text/html" and not text_html:
            raw = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            if raw:
                text_html = raw.decode(charset, errors="replace")

    if text_plain:
        return text_plain.strip()
    return _strip_html(text_html).strip()


# ── attachment extraction ─────────────────────────────────────────────────────

def extract_file_parts(msg: Message) -> list[tuple[str, bytes]]:
    """Return ``(filename, raw_bytes)`` for each MIME part that may be an image or PDF.

    The content-type header is *not* trusted — the ``TicketService`` validates
    each binary blob against its magic bytes before saving.
    """
    results: list[tuple[str, bytes]] = []
    if not msg.is_multipart():
        return results

    for count, part in enumerate(msg.walk()):
        if count >= _MAX_MIME_PARTS:
            logger.warning("email-ingestion: MIME part limit (%d) reached — truncating attachment extraction", _MAX_MIME_PARTS)
            break
        ct = part.get_content_type()
        disp = part.get_content_disposition() or ""
        # Only process parts that look like they could be images or PDFs.
        # Magic-byte validation happens inside TicketService.add_attachment_bytes.
        if ct.startswith("image/") or ct == "application/pdf" or "attachment" in disp:
            raw = part.get_payload(decode=True)
            if not raw:
                continue
            filename = part.get_filename() or _fallback_filename(ct)
            results.append((filename, raw))

    return results


def _fallback_filename(content_type: str) -> str:
    ext_map = {
        "image/jpeg": "image.jpg",
        "image/png": "image.png",
        "image/gif": "image.gif",
        "image/webp": "image.webp",
        "application/pdf": "document.pdf",
    }
    return ext_map.get(content_type, "attachment.bin")


# ── ingestion service ─────────────────────────────────────────────────────────

class EmailIngestionService:
    """Processes a single raw RFC 2822 message and persists it to the database."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ingest(self, raw_message: bytes) -> bool:
        """Parse *raw_message* and write comment + attachments if a ticket is found.

        Returns ``True`` when the message was successfully ingested, ``False``
        when it was deliberately skipped (unknown ticket, no author, etc.).
        Raises for unexpected database / I/O errors so the caller can decide
        whether to mark the message as seen or leave it for a retry.
        """
        msg = email_lib.message_from_bytes(raw_message)
        subject = msg.get("Subject", "") or ""
        from_addr = _parse_from_addr(msg.get("From", "") or "")

        # Guard: reject oversized messages before any further parsing (DoS protection).
        max_bytes = settings.IMAP_MAX_MESSAGE_SIZE_MB * 1024 * 1024
        if len(raw_message) > max_bytes:
            logger.warning(
                "email-ingestion: message from %r exceeds size limit (%d MB) — skipping",
                from_addr,
                settings.IMAP_MAX_MESSAGE_SIZE_MB,
            )
            return False

        ticket_num = parse_ticket_number(subject)
        if ticket_num is None:
            logger.debug("email-ingestion: no ticket reference in subject %r — skipping", subject)
            return False

        # Resolve ticket
        result = await self.db.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_num)
        )
        ticket = result.scalar_one_or_none()
        if ticket is None:
            logger.warning(
                "email-ingestion: subject %r references ticket #%d which does not exist",
                subject, ticket_num,
            )
            return False

        # Resolve author — rejects message if sender is not an approved registered user
        # (when IMAP_REQUIRE_REGISTERED_SENDER=true, the default).
        author = await self._resolve_author(from_addr)
        if author is None:
            logger.warning(
                "email-ingestion: rejected message for ticket #%d — sender %r is not a "
                "registered/approved user and IMAP_REQUIRE_REGISTERED_SENDER=%s",
                ticket_num, from_addr, settings.IMAP_REQUIRE_REGISTERED_SENDER,
            )
            return False

        # Org-scope check: non-superuser senders may only comment on tickets that
        # belong to their own organisation.  Without this check a registered user in
        # org A could post comments on any ticket in org B simply by knowing its number.
        if not author.is_superuser and author.organization_id != ticket.organization_id:
            logger.warning(
                "email-ingestion: rejected message for ticket #%d — sender %r belongs to "
                "org %s but ticket belongs to org %s",
                ticket_num, from_addr, author.organization_id, ticket.organization_id,
            )
            return False

        author_id = author.id

        # Build comment content — prefix with sender info only in system-user fallback
        # mode (permissive mode), where the DB author is not the actual sender.
        body = extract_text_body(msg)
        if not body:
            body = "(no text content)"

        is_system_author = (
            not settings.IMAP_REQUIRE_REGISTERED_SENDER
            and settings.IMAP_SYSTEM_USER_EMAIL
            and author.email == settings.IMAP_SYSTEM_USER_EMAIL.lower()
        )
        sender_prefix = f"📧 **From:** {from_addr}\n\n" if (from_addr and is_system_author) else ""
        raw_comment = f"{sender_prefix}{body}"
        # Cap to prevent enormous email bodies from bloating the database.
        comment_content = raw_comment[:_MAX_COMMENT_LENGTH]

        comment = Comment(
            ticket_id=ticket.id,
            author_id=author_id,
            content=comment_content,
        )
        self.db.add(comment)
        await self.db.flush()

        # Save attachments
        svc = TicketService(self.db)
        saved = 0
        skipped = 0
        for filename, raw_bytes in extract_file_parts(msg):
            attachment = await svc.add_attachment_bytes(ticket, raw_bytes, filename, author_id)
            if attachment is not None:
                saved += 1
            else:
                skipped += 1
                logger.debug(
                    "email-ingestion: skipped unsupported or oversized part %r for ticket #%d",
                    filename, ticket_num,
                )

        logger.info(
            "email-ingestion: ticket #%d — comment added, %d attachment(s) saved, %d skipped",
            ticket_num, saved, skipped,
        )
        return True

    async def _resolve_author(self, from_email: str) -> User | None:
        """Return the User to attribute this email to, or ``None`` to reject.

        When ``IMAP_REQUIRE_REGISTERED_SENDER=true`` (the default) only messages
        from a known, active user account are accepted — all other senders are
        rejected and the message is discarded unpersisted.

        When ``IMAP_REQUIRE_REGISTERED_SENDER=false`` an unrecognised sender falls
        back to the ``IMAP_SYSTEM_USER_EMAIL`` account.  If that is also unset or
        unresolvable the message is still discarded; there is intentionally **no**
        further fallback to superuser accounts.

        Returns the full User object so the caller can check organisation membership
        and whether the user is a superuser (for org-scope access control).
        """
        # Always try to match the sender to a registered, active user first.
        if from_email:
            result = await self.db.execute(
                select(User).where(
                    User.email == from_email.lower(),
                    User.is_active.is_(True),
                    User.is_approved.is_(True),
                )
            )
            user = result.scalar_one_or_none()
            if user:
                return user

        # Sender not found in the user table.
        if settings.IMAP_REQUIRE_REGISTERED_SENDER:
            # Strict mode (default): reject unknown senders.
            return None

        # Permissive mode: attribute to the configured system user.
        # Deliberately no fallback to superuser — that would allow arbitrary
        # external parties to inject content attributed to an admin account.
        if settings.IMAP_SYSTEM_USER_EMAIL:
            result = await self.db.execute(
                select(User).where(
                    User.email == settings.IMAP_SYSTEM_USER_EMAIL.lower(),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()
            if user:
                return user

        return None


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_from_addr(header_value: str) -> str:
    """Extract the bare email address from a From: header value.

    Handles both ``User Name <user@example.com>`` and ``user@example.com``.
    """
    if not header_value:
        return ""
    # email.utils.parseaddr is stdlib and handles RFC 2822 address formats
    from email.utils import parseaddr
    _name, addr = parseaddr(header_value)
    return addr.lower().strip()
