"""IMAP polling loop for email-to-ticket ingestion.

Polls the configured IMAP mailbox for UNSEEN messages on a fixed interval.
Each unseen message is passed to ``EmailIngestionService.ingest()``.  Messages
are marked SEEN after a successful ingest *or* a deliberate skip (unknown
ticket, etc.).  Messages that cause an unexpected error are left UNSEEN so
they are retried on the next poll cycle.

The poller runs as a background asyncio task started in the FastAPI lifespan
(``app/main.py``).  Use ``poll_once()`` for a single synchronous-style poll
(e.g., from the admin endpoint for manual triggering).
"""

from __future__ import annotations

import asyncio
import imaplib
import logging
import ssl
from dataclasses import dataclass, field

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.email_ingestion import EmailIngestionService

logger = logging.getLogger(__name__)


@dataclass
class PollResult:
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)


_IMAP_TIMEOUT = 30  # seconds — prevents hung server from pinning the thread-pool worker


def _imap_connect() -> imaplib.IMAP4 | imaplib.IMAP4_SSL:
    """Open and authenticate an IMAP connection.  Runs in a thread-pool worker."""
    if settings.IMAP_USE_SSL:
        ctx = ssl.create_default_context()
        conn: imaplib.IMAP4 | imaplib.IMAP4_SSL = imaplib.IMAP4_SSL(
            host=settings.IMAP_HOST,
            port=settings.IMAP_PORT,
            ssl_context=ctx,
            timeout=_IMAP_TIMEOUT,
        )
    else:
        conn = imaplib.IMAP4(
            host=settings.IMAP_HOST,
            port=settings.IMAP_PORT,
            timeout=_IMAP_TIMEOUT,
        )

    conn.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
    return conn


def _fetch_unseen_raw(conn: imaplib.IMAP4 | imaplib.IMAP4_SSL) -> list[tuple[bytes, bytes]]:
    """Select the mailbox and return ``[(uid, raw_rfc822), …]`` for UNSEEN messages."""
    conn.select(settings.IMAP_MAILBOX)
    _status, data = conn.uid("SEARCH", None, "UNSEEN")  # type: ignore[call-overload]
    if not data or not data[0]:
        return []

    uid_list = data[0].split()
    results: list[tuple[bytes, bytes]] = []
    for uid in uid_list:
        _s, msg_data = conn.uid("FETCH", uid, "(RFC822)")  # type: ignore[call-overload]
        if msg_data and msg_data[0]:
            raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
            results.append((uid, raw))  # type: ignore[arg-type]
    return results


def _mark_seen(conn: imaplib.IMAP4 | imaplib.IMAP4_SSL, uid: bytes) -> None:
    conn.uid("STORE", uid, "+FLAGS", "\\Seen")  # type: ignore[call-overload]


async def poll_once() -> PollResult:
    """Fetch UNSEEN messages from the IMAP mailbox and ingest them.

    Each message that is successfully ingested (or deliberately skipped) is
    marked as SEEN.  Messages that raise an unexpected exception are left
    UNSEEN for the next poll cycle.

    Returns a ``PollResult`` summarising what happened.
    """
    result = PollResult()

    loop = asyncio.get_running_loop()

    try:
        conn = await loop.run_in_executor(None, _imap_connect)
    except Exception as exc:
        logger.error("email-ingestion: IMAP connection failed: %s", exc)
        result.error_details.append(f"IMAP connection: {exc}")
        result.errors += 1
        return result

    try:
        messages = await loop.run_in_executor(None, _fetch_unseen_raw, conn)
    except Exception as exc:
        logger.error("email-ingestion: failed to fetch messages: %s", exc)
        result.error_details.append(f"IMAP fetch: {exc}")
        result.errors += 1
        conn.logout()
        return result

    for uid, raw in messages:
        mark_seen_after = False
        async with AsyncSessionLocal() as db:
            async with db.begin():
                try:
                    svc = EmailIngestionService(db)
                    ingested = await svc.ingest(raw)
                    if ingested:
                        result.processed += 1
                    else:
                        result.skipped += 1
                    # Signal that we should mark the message seen *after* the DB
                    # transaction commits.  Doing it inside the transaction would
                    # create a window where the DB commits but _mark_seen raises,
                    # leaving the message UNSEEN and causing a duplicate comment on
                    # the next poll cycle.
                    mark_seen_after = True
                except Exception as exc:
                    # Leave UNSEEN so the next poll cycle retries.
                    logger.exception(
                        "email-ingestion: unexpected error processing message uid=%r: %s",
                        uid, exc,
                    )
                    result.errors += 1
                    result.error_details.append(str(exc))
                    # Roll back is automatic when the context manager exits with an exception.

        # DB transaction has committed.  Now mark the message seen in IMAP.
        # A failure here is non-fatal: the comment already exists in the DB and the
        # next poll would find an already-handled message.  Log and continue.
        if mark_seen_after:
            try:
                await loop.run_in_executor(None, _mark_seen, conn, uid)
            except Exception as exc:
                logger.warning(
                    "email-ingestion: failed to mark message uid=%r as seen (will retry on next poll): %s",
                    uid, exc,
                )

    try:
        conn.logout()
    except Exception:
        pass

    return result


async def run_forever() -> None:
    """Background task: poll on a fixed interval until cancelled."""
    logger.info(
        "email-ingestion: poller started — mailbox=%s host=%s interval=%ds",
        settings.IMAP_MAILBOX,
        settings.IMAP_HOST,
        settings.IMAP_POLL_INTERVAL_SECONDS,
    )
    while True:
        try:
            result = await poll_once()
            if result.processed or result.errors:
                logger.info(
                    "email-ingestion: poll complete — processed=%d skipped=%d errors=%d",
                    result.processed, result.skipped, result.errors,
                )
        except asyncio.CancelledError:
            logger.info("email-ingestion: poller cancelled")
            raise
        except Exception as exc:
            logger.exception("email-ingestion: unhandled error in poll loop: %s", exc)

        await asyncio.sleep(settings.IMAP_POLL_INTERVAL_SECONDS)
