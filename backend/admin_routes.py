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


@admin_router.patch("/employees/{employee_id}/review", dependencies=[Depends(require_admin)])
def update_review_status(employee_id: str, payload: ReviewIn) -> dict[str, Any]:
    db = _get_db()
    doc_ref = db.collection("employee_summary").document(employee_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="employee_summary not found")
    update = {
        "review_status": payload.review_status,
        "review_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.review_note is not None:
        update["review_note"] = payload.review_note
    doc_ref.update(update)
    return {"employee_id": employee_id, **update}
