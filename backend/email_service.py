"""Resend email helper + simple Firestore audit log.

Strict secret hygiene:
- API key is read from os.environ['RESEND_API_KEY'] only.
- Nothing about the key is ever returned to the caller or logged.
- During Resend "test mode", the provider only delivers to the API-key owner.
  Setting RESEND_TEST_OVERRIDE_EMAIL routes every recipient there so HR can
  see the emails arrive end-to-end before the PNC domain is verified.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import resend

logger = logging.getLogger("pnc.email")


class EmailSendError(RuntimeError):
    pass


def _configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def _sender() -> str:
    return os.environ.get("SENDER_EMAIL") or "onboarding@resend.dev"


def _resolve_recipient(to: str) -> tuple[str, str | None]:
    """Apply the test-mode override, if any."""
    override = os.environ.get("RESEND_TEST_OVERRIDE_EMAIL")
    if override and override.strip().lower() != to.strip().lower():
        return override.strip(), to
    return to, None


def _log_email(db, payload: dict[str, Any]) -> None:
    try:
        db.collection("email_logs").add(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write email_log: %s", exc)


async def send_email(
    db,
    *,
    to: str,
    subject: str,
    html: str,
    purpose: str,
    employee_id: str | None = None,
) -> dict[str, Any]:
    """Send a transactional email via Resend and write an audit log to
    Firestore (`email_logs` collection).

    Returns a dict with status, message_id, and a flag indicating whether the
    test-mode override redirected the message.
    """
    if not _configured():
        record = {
            "to": to,
            "subject": subject,
            "purpose": purpose,
            "employee_id": employee_id,
            "status": "skipped_not_configured",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _log_email(db, record)
        return {"status": "skipped", "reason": "resend_not_configured"}

    resend.api_key = os.environ["RESEND_API_KEY"]

    actual_to, original_to = _resolve_recipient(to)
    params: dict[str, Any] = {
        "from": _sender(),
        "to": [actual_to],
        "subject": subject,
        "html": html,
    }

    record: dict[str, Any] = {
        "to": to,
        "actual_recipient": actual_to,
        "redirected_from": original_to,
        "subject": subject,
        "purpose": purpose,
        "employee_id": employee_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        record["status"] = "sent"
        record["message_id"] = (email or {}).get("id")
        _log_email(db, record)
        return {
            "status": "sent",
            "message_id": record["message_id"],
            "redirected": original_to is not None,
            "actual_recipient": actual_to,
        }
    except Exception as exc:  # noqa: BLE001
        # Do not include any header that might echo the key.
        msg = type(exc).__name__
        record["status"] = "failed"
        record["error"] = msg
        _log_email(db, record)
        logger.error("Resend send failed: %s", msg)
        raise EmailSendError(msg)
