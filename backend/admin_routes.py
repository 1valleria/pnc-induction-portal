"""Admin-protected endpoints for HR.

All routes here require HTTP Basic Auth using ADMIN_USERNAME / ADMIN_PASSWORD
from backend/.env. Designed for use by HR tooling (Excel "From Web", scripts,
internal dashboards) — never expose these credentials in the frontend.
"""
from __future__ import annotations

import csv
import io
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

admin_router = APIRouter(prefix="/api/admin")
_basic = HTTPBasic(realm="PNC Admin")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def require_admin(creds: HTTPBasicCredentials = Depends(_basic)) -> str:
    expected_user = os.environ.get("ADMIN_USERNAME")
    expected_pass = os.environ.get("ADMIN_PASSWORD")
    if not expected_user or not expected_pass:
        raise HTTPException(
            status_code=500,
            detail="Admin credentials are not configured on the server.",
        )
    ok_user = secrets.compare_digest(creds.username, expected_user)
    ok_pass = secrets.compare_digest(creds.password, expected_pass)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": 'Basic realm="PNC Admin"'},
        )
    return creds.username


# ---------------------------------------------------------------------------
# CSV column order — mirrors PNC's existing subcontractor spreadsheet so HR
# can stop using the old workflow without retraining. Each entry is
# (human-readable header, source field on employee_summary).
# ---------------------------------------------------------------------------


CSV_SCHEMA: list[tuple[str, str]] = [
    ("Name", "full_name"),
    ("Date Of Birth", "dob"),
    ("Address", "address1"),
    ("Post Code", "postcode"),
    ("Phone Number", "telephone"),
    ("Email Address", "email"),
    ("NI Number", "ni_number"),
    ("Induction Status", "induction_status"),
    ("Medical Status", "medical_status"),
    ("Driving Licence", "driving_licence_url"),
    ("Driving Licence Check", "dvla_check"),
    ("Passport", "passport_url"),
    ("Right To Work", "right_to_work_share_code"),
    ("Proof Of Bank", "bank_proof_url"),
    ("Business Name", "company_name"),
    ("Account Number", "bank_account"),
    ("Sort Code", "sort_code"),
    ("VAT Number", "vat_number"),
    ("UTR", "utr"),
    ("Review Status", "review_status"),
    ("PDF Link", "pdf_url"),
    # Identity column kept last so it's easy to ignore when humans read the
    # spreadsheet but available for scripts that need a stable key.
    ("Employee ID", "employee_id"),
    ("Submitted At", "submitted_at"),
]

# Legacy single-list form (some tests still import this name)
CSV_COLUMNS: list[str] = [label for label, _ in CSV_SCHEMA]


def _format_csv_value(label: str, value: Any) -> str:
    """Tighten a few columns for HR readability."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if label == "Driving Licence Check":
        v = str(value).strip().lower()
        return "Yes" if v == "yes" else "No" if v == "no" else str(value)
    if label == "Review Status":
        return {
            "pending_review": "Pending Review",
            "approved": "Approved",
            "rejected": "Rejected",
        }.get(str(value), str(value))
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


# ---------------------------------------------------------------------------
# Search/filter
# ---------------------------------------------------------------------------


def _matches(record: dict, *, q: str | None, email: str | None, ni: str | None,
             company: str | None, date_from: str | None, date_to: str | None,
             review_status: str | None) -> bool:
    if q:
        needle = q.lower()
        full_name = (record.get("full_name") or "").lower()
        if needle not in full_name:
            return False
    if email:
        rec_email = (record.get("email") or "").lower()
        if email.lower() not in rec_email:
            return False
    if ni:
        rec_ni = (record.get("ni_number") or "").lower()
        if ni.lower() not in rec_ni:
            return False
    if company:
        rec_company = (record.get("company_name") or "").lower()
        if company.lower() not in rec_company:
            return False
    if review_status:
        if (record.get("review_status") or "") != review_status:
            return False
    if date_from or date_to:
        submitted = record.get("submitted_at") or ""
        # ISO strings compare lexicographically when zero-padded
        if date_from and submitted and submitted < date_from:
            return False
        if date_to and submitted and submitted > date_to + "T23:59:59Z":
            return False
    return True


def _stream_employees(records: list[dict]):
    """Yield CSV bytes (with UTF-8 BOM so Excel opens it correctly)."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    headers = [label for label, _ in CSV_SCHEMA]
    writer.writerow(headers)
    yield "\ufeff" + buf.getvalue()  # BOM then header
    buf.seek(0)
    buf.truncate(0)
    for rec in records:
        writer.writerow(
            [_format_csv_value(label, rec.get(key)) for label, key in CSV_SCHEMA]
        )
        chunk = buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        yield chunk


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class ReviewIn(BaseModel):
    review_status: str = Field(..., pattern="^(pending_review|approved|rejected)$")
    review_note: str | None = Field(default=None, max_length=2000)


def _get_db():
    # Imported lazily so the module loads without Firebase being configured
    from firebase_client import get_firestore
    return get_firestore()


@admin_router.get("/employees", dependencies=[Depends(require_admin)])
def list_employees(
    q: str | None = Query(default=None, description="Search in full_name"),
    email: str | None = Query(default=None),
    ni: str | None = Query(default=None, description="Partial NI number"),
    company: str | None = Query(default=None),
    review_status: str | None = Query(default=None, pattern="^(pending_review|approved|rejected)$"),
    date_from: str | None = Query(default=None, description="ISO date, e.g. 2026-01-01"),
    date_to: str | None = Query(default=None, description="ISO date, e.g. 2026-12-31"),
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict[str, Any]:
    db = _get_db()
    records: list[dict] = []
    for doc in db.collection("employee_summary").stream():
        rec = doc.to_dict() or {}
        if _matches(rec, q=q, email=email, ni=ni, company=company,
                    date_from=date_from, date_to=date_to, review_status=review_status):
            records.append(rec)
        if len(records) >= limit:
            break
    # newest submission first
    records.sort(key=lambda r: r.get("submitted_at") or "", reverse=True)
    return {"count": len(records), "items": records}


@admin_router.get("/employees.csv", dependencies=[Depends(require_admin)])
def export_employees_csv(
    q: str | None = Query(default=None),
    email: str | None = Query(default=None),
    ni: str | None = Query(default=None),
    company: str | None = Query(default=None),
    review_status: str | None = Query(default=None, pattern="^(pending_review|approved|rejected)$"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    db = _get_db()
    records: list[dict] = []
    for doc in db.collection("employee_summary").stream():
        rec = doc.to_dict() or {}
        if _matches(rec, q=q, email=email, ni=ni, company=company,
                    date_from=date_from, date_to=date_to, review_status=review_status):
            records.append(rec)
    records.sort(key=lambda r: r.get("submitted_at") or "", reverse=True)

    filename = f"pnc-employees-{datetime.now(timezone.utc):%Y%m%d-%H%M}.csv"
    return StreamingResponse(
        _stream_employees(records),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@admin_router.get("/system-status", dependencies=[Depends(require_admin)])
def system_status() -> dict[str, Any]:
    """Expose the safety-relevant runtime config so the Admin Portal can show
    a clear 'Test Mode' banner when emails are being redirected."""
    override = os.environ.get("RESEND_TEST_OVERRIDE_EMAIL")
    sender = os.environ.get("SENDER_EMAIL") or "onboarding@resend.dev"
    portal = os.environ.get("PUBLIC_PORTAL_URL") or ""
    return {
        "email_test_mode": bool(override),
        "email_redirect_to": override or None,
        "sender_email": sender,
        "portal_url": portal,
        "resend_configured": bool(os.environ.get("RESEND_API_KEY")),
    }


@admin_router.patch("/employees/{employee_id}/review", dependencies=[Depends(require_admin)])
async def update_review_status(employee_id: str, payload: ReviewIn) -> dict[str, Any]:
    from email_service import EmailSendError, send_email
    from email_templates import approval, rejection

    db = _get_db()
    doc_ref = db.collection("employee_summary").document(employee_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="employee_summary not found")
    rec = snap.to_dict() or {}
    previous = rec.get("review_status")
    now_iso = datetime.now(timezone.utc).isoformat()
    update: dict[str, Any] = {
        "review_status": payload.review_status,
        "review_updated_at": now_iso,
        "reviewed_at": now_iso,
    }
    if payload.review_note is not None:
        update["review_note"] = payload.review_note

    # Rejection-only: mint a fresh access code so the inductee can resubmit.
    new_access_code: str | None = None
    new_access_code_id: str | None = None
    portal_url = os.environ.get("PUBLIC_PORTAL_URL") or "https://induct-pro.emergent.host"
    is_rejection = payload.review_status == "rejected" and previous != "rejected"
    if is_rejection:
        new_access_code = _new_unique_code(db)
        invite_doc = db.collection("access_codes").document()
        invite_doc.set({
            "code": new_access_code,
            "email": (rec.get("email") or rec.get("invited_email") or "").strip().lower() or None,
            "full_name": rec.get("full_name") or "",
            "used": False,
            "employee_id": "",
            "invite_status": "resent_after_rejection",
            "created_at": now_iso,
            "invited_at": now_iso,
            "invited_at_server": datetime.now(timezone.utc),
            "related_rejected_employee_id": employee_id,
            "rejection_reason": payload.review_note or "",
        })
        new_access_code_id = invite_doc.id
        update["resubmission_code"] = new_access_code
        update["resubmission_requested"] = True
        update["resubmission_access_code_id"] = new_access_code_id

    doc_ref.update(update)

    # Side-effect: notify inductee on approval / rejection transitions.
    email_status: str | None = None
    to = rec.get("email") or rec.get("invited_email")
    if to and payload.review_status != previous and payload.review_status in {"approved", "rejected"}:
        try:
            if payload.review_status == "approved":
                subject, html = approval(rec.get("full_name") or "")
            else:
                subject, html = rejection(
                    rec.get("full_name") or "",
                    payload.review_note,
                    portal_url=portal_url,
                    email=to,
                    new_code=new_access_code,
                )
            result = await send_email(
                db,
                to=to,
                subject=subject,
                html=html,
                purpose=f"review_{payload.review_status}",
                employee_id=employee_id,
            )
            email_status = result.get("status")
        except EmailSendError:
            email_status = "failed"

    response: dict[str, Any] = {
        "employee_id": employee_id,
        "email_status": email_status,
        **update,
    }
    if new_access_code:
        invitation_text = (
            "PNC Induction — Resubmission\n\n"
            f"Hi {(rec.get('full_name') or '').strip()},\n\n"
            "Your previous induction submission needs additional information. "
            "Please complete the induction form again using the new access code below.\n\n"
            f"{portal_url}\n\n"
            f"Email: {to or '(use your own email)'}\n"
            f"New Access Code: {new_access_code}\n\n"
            "Reason from PNC HR:\n"
            f"{payload.review_note or ''}\n"
        )
        response["new_access_code"] = new_access_code
        response["new_access_code_id"] = new_access_code_id
        response["invitation_text"] = invitation_text
        response["portal_url"] = portal_url
    return response


# ---------------------------------------------------------------------------
# Invitations — create + list
# ---------------------------------------------------------------------------


def _generate_code() -> str:
    """Generate a short, human-friendly access code: PNC-XXXX-XXXX (alphanumeric).
    Avoid ambiguous characters (0, O, 1, I, L)."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    def _block() -> str:
        return "".join(secrets.choice(alphabet) for _ in range(4))
    return f"PNC-{_block()}-{_block()}"


def _new_unique_code(db) -> str:
    for _ in range(8):
        code = _generate_code()
        existing = list(db.collection("access_codes").where("code", "==", code).limit(1).stream())
        if not existing:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique access code")


class InviteIn(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=200)
    send_email: bool = True


@admin_router.post("/invites", dependencies=[Depends(require_admin)])
async def create_invite(payload: InviteIn) -> dict[str, Any]:
    from email_service import EmailSendError, send_email
    from email_templates import invitation

    db = _get_db()
    code = _new_unique_code(db)
    now = datetime.now(timezone.utc).isoformat()
    portal_url = os.environ.get("PUBLIC_PORTAL_URL") or "https://induct-pro.emergent.host"
    normalised_email = (payload.email or "").strip().lower() or None

    doc_payload = {
        "code": code,
        "email": normalised_email,
        "full_name": payload.full_name.strip(),
        "used": False,
        "employee_id": "",
        "invited_at": now,
        "invited_at_server": datetime.now(timezone.utc),
        "invite_status": "sent" if (payload.send_email and normalised_email) else "created",
        "delivery": None,
    }
    ref = db.collection("access_codes").document()
    ref.set(doc_payload)

    email_result: dict[str, Any] | None = None
    if payload.send_email and normalised_email:
        try:
            subject, html = invitation(
                full_name=payload.full_name.strip(),
                portal_url=portal_url,
                email=normalised_email,
                code=code,
            )
            email_result = await send_email(
                db,
                to=normalised_email,
                subject=subject,
                html=html,
                purpose="invitation",
            )
            ref.update({"delivery": email_result, "invite_status": "sent"})
        except EmailSendError as exc:
            ref.update({"invite_status": "failed", "delivery": {"status": "failed", "error": str(exc)}})
            email_result = {"status": "failed"}

    invite_text = (
        "PNC Induction\n\n"
        f"Hi {payload.full_name.strip()},\n\n"
        "Please complete your induction:\n"
        f"{portal_url}\n\n"
        f"Email: {normalised_email or '(use your own email)'}\n"
        f"Access Code: {code}\n"
    )

    return {
        "id": ref.id,
        "code": code,
        "full_name": payload.full_name.strip(),
        "email": normalised_email,
        "portal_url": portal_url,
        "invitation_text": invite_text,
        "invite_status": "sent" if (payload.send_email and normalised_email and email_result and email_result.get("status") == "sent") else doc_payload["invite_status"],
        "email_result": email_result,
        "invited_at": now,
    }


@admin_router.get("/invites", dependencies=[Depends(require_admin)])
def list_invites(limit: int = Query(default=500, ge=1, le=2000)) -> dict[str, Any]:
    db = _get_db()
    items: list[dict[str, Any]] = []
    for doc in db.collection("access_codes").stream():
        d = doc.to_dict() or {}
        delivery = d.get("delivery") if isinstance(d.get("delivery"), dict) else {}
        items.append(
            {
                "id": doc.id,
                "code": d.get("code"),
                "full_name": d.get("full_name"),
                "email": d.get("email"),
                "used": bool(d.get("used")),
                "employee_id": d.get("employee_id") or None,
                "invite_status": d.get("invite_status") or ("used" if d.get("used") else "created"),
                "invited_at": d.get("invited_at"),
                "used_at": d.get("used_at") if not hasattr(d.get("used_at"), "isoformat") else d["used_at"].isoformat(),
                "delivery_status": (delivery or {}).get("status"),
                "delivery_redirected_to": (delivery or {}).get("actual_recipient") if (delivery or {}).get("redirected") else None,
            }
        )
    # newest invited_at first; fall back to created
    items.sort(key=lambda r: (r.get("invited_at") or ""), reverse=True)
    return {"count": len(items), "items": items[:limit]}
