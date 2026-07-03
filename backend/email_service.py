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
        logger.info(
            "email.sent purpose=%s to=%s message_id=%s redirected=%s",
            purpose, actual_to, record["message_id"], original_to is not None,
        )
        return {
            "status": "sent",
            "message_id": record["message_id"],
            "redirected": original_to is not None,
            "actual_recipient": actual_to,
        }
    except Exception as exc:  # noqa: BLE001
        # Extract as much diagnostic detail as safely possible from the Resend
        # exception without leaking the API key. The resend-python SDK raises
        # exceptions whose `.args`, `.message`, `.code`, or `.status_code`
        # carry the useful info; we capture all of them defensively.
        cls = type(exc).__name__
        detail: dict[str, Any] = {"error_class": cls}
        for attr in ("status_code", "code", "message", "error_type", "name"):
            val = getattr(exc, attr, None)
            if val is not None:
                detail[attr] = str(val)[:400]
        # str(exc) usually contains a JSON blob from Resend; keep it capped.
        if str(exc):
            detail["message_body"] = str(exc)[:400]
        # Sanitise anything that might contain the API key just in case.
        api_key = os.environ.get("RESEND_API_KEY") or ""
        if api_key:
            for k, v in list(detail.items()):
                if isinstance(v, str) and api_key in v:
                    detail[k] = v.replace(api_key, "<REDACTED_API_KEY>")

        record["status"] = "failed"
        record["error"] = detail
        _log_email(db, record)
        # Structured log line — searchable in Cloud Run / Emergent logs.
        logger.error(
            "email.send_failed purpose=%s to=%s error_class=%s status_code=%s message=%s",
            purpose, actual_to, cls, detail.get("status_code"), detail.get("message_body"),
        )
        # Human-readable string for the API response / EmailSendError message
        summary_parts: list[str] = [cls]
        if detail.get("status_code"):
            summary_parts.append(f"HTTP {detail['status_code']}")
        if detail.get("message_body"):
            summary_parts.append(detail["message_body"])
        raise EmailSendError(" — ".join(summary_parts))
