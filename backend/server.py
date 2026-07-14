"""PNC Induction Portal — backend.

Phase 2 endpoint: POST /api/induction/finalize
  - Reads employee + medical_history + havs_questionnaires + employee_documents
    from Firestore.
  - Generates a professional PDF (reportlab).
  - Uploads the PDF to Firebase Storage at employees/{id}/pdf/induction-{id}.pdf.
  - Writes pdf_url back to the employee_documents doc.
  - Creates a single, denormalised employee_summary doc that acts as the master
    HR record (replacing the CSV workflow).
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pnc")


# Disable interactive docs + OpenAPI JSON in production so the surface is not
# exposed to reputation scanners / recon tooling. Set APP_ENV=development in
# local .env to re-enable them for debugging.
_APP_ENV = (os.environ.get("APP_ENV") or "production").lower()
_ENABLE_DOCS = _APP_ENV != "production"
app = FastAPI(
    title="Contractor Induction API",
    docs_url="/docs" if _ENABLE_DOCS else None,
    redoc_url="/redoc" if _ENABLE_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_DOCS else None,
)
api_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FinalizeIn(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=128)


class FinalizeOut(BaseModel):
    employee_id: str
    pdf_url: str
    employee_summary_id: str
    generated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_first_doc(query) -> dict | None:
    """Return the first doc.to_dict() from a Firestore query (or None)."""
    for d in query.stream():
        data = d.to_dict() or {}
        data["__doc_id__"] = d.id
        return data
    return None


def _fetch_employee_bundle(db, employee_id: str) -> dict[str, Any]:
    """Read all 4 collections related to the employee in one go."""
    emp_doc = db.collection("employees").document(employee_id).get()
    if not emp_doc.exists:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee = emp_doc.to_dict() or {}

    medical = (
        _get_first_doc(
            db.collection("medical_history").where("employee_id", "==", employee_id).limit(1)
        )
        or {}
    )
    havs = (
        _get_first_doc(
            db.collection("havs_questionnaires").where("employee_id", "==", employee_id).limit(1)
        )
        or {}
    )
    docs = (
        _get_first_doc(
            db.collection("employee_documents").where("employee_id", "==", employee_id).limit(1)
        )
        or {}
    )
    return {
        "employee": employee,
        "medical": medical,
        "havs": havs,
        "documents": docs,
    }


def _download_signature_bytes(bucket, files: dict) -> bytes | None:
    sig = files.get("signature") or {}
    path = sig.get("path")
    if not path:
        return None
    try:
        blob = bucket.blob(path)
        if not blob.exists():
            return None
        return blob.download_as_bytes()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to download signature image (%s): %s", path, exc)
        return None


def _make_public_url(bucket, blob) -> str:
    """Return a long-lived download URL (token-based) without requiring a CDN."""
    try:
        # Firebase Hosting-style URL works without `firebaseConfig` quirks.
        # Use a download token so the URL is stable and shareable.
        import uuid as _uuid

        token = _uuid.uuid4().hex
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.patch()
        bucket_name = bucket.name
        path = blob.name.replace("/", "%2F")
        return (
            f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{path}"
            f"?alt=media&token={token}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falling back to gs:// URL: %s", exc)
        return f"gs://{bucket.name}/{blob.name}"


def _resolve_storage_folder(documents_doc: dict, employee: dict, employee_id: str) -> tuple[str, bool]:
    """Return (storage_folder_path, is_legacy).

    - If employee_documents.storage_folder_path exists (new submissions) → use it.
    - Otherwise the record was created BEFORE the folder-naming change. We
      strictly preserve its legacy `employees/{employee_id}/` path so existing
      records and their PDFs stay where HR/Firebase Console already finds them.
    The `employee` argument is unused in legacy mode — kept for future
    convenience (e.g. a one-time migration script).
    """
    explicit = (documents_doc or {}).get("storage_folder_path")
    if explicit:
        return (explicit if explicit.endswith("/") else explicit + "/"), False
    # Legacy fallback — do NOT derive a new path for old records
    return f"employees/{employee_id}/", True


def _compute_missing_documents(emp: dict, files: dict) -> list[str]:
    """Return a list of slots that should be present but aren't."""
    required = ["passport", "driving_licence", "bank_proof"]
    if (emp.get("insurance_option") or "").lower() == "own":
        required.append("insurance_certificate")
    # `signature` is always expected (drawn signature image)
    required.append("signature")
    return [slot for slot in required if not (files.get(slot) or {}).get("url")]


_MEDICAL_KEYS = [
    "receiving_treatment", "prescribed_medication", "medical_warning_card",
    "pregnant", "allergies", "asthma_bronchitis_chest",
    "fainting_blackouts_epilepsy", "heart_problems", "diabetes",
    "bone_or_joint_disease", "skin_disease", "persistent_bleeding_bruising",
    "liver_or_kidney_disease", "havs_or_cts", "other_serious_illness",
]


def _compute_medical_status(med: dict) -> str:
    """HR-friendly summary of the medical questionnaire.

    Returns:
        "Disclosed"  — at least one Yes (HR review recommended)
        "Clear"      — every question answered No
        "Incomplete" — at least one question missing an answer
    """
    answers = [med.get(k) for k in _MEDICAL_KEYS]
    if any(a == "yes" for a in answers):
        return "Disclosed"
    if all(a == "no" for a in answers):
        return "Clear"
    return "Incomplete"


def _compute_induction_status(missing_documents: list[str], pdf_url: str | None) -> str:
    """High-level status mirroring the HR spreadsheet's "Induction Status" column."""
    if missing_documents:
        return "Awaiting Documents"
    if not pdf_url:
        return "Pending"
    return "Complete"


def _doc_status(url: str | None) -> str:
    return "Uploaded" if url else "Missing"


def _flatten_for_summary(bundle: dict, pdf_url: str, employee_id: str, storage_folder_path: str) -> dict[str, Any]:
    """Denormalise everything into one doc that an HR person can read top-to-bottom
    or export as a CSV row."""
    emp = bundle["employee"] or {}
    med = bundle["medical"] or {}
    havs = bundle["havs"] or {}
    docs = bundle["documents"] or {}
    files = docs.get("files") or {}

    def url_of(slot: str) -> str | None:
        return (files.get(slot) or {}).get("url")

    now = datetime.now(timezone.utc).isoformat()
    emergency = emp.get("emergency_contact") or {}
    biz = emp.get("business") or {}

    summary = {
        "employee_id": employee_id,
        "storage_folder_path": storage_folder_path,
        # --- personal
        "full_name": emp.get("full_name"),
        "dob": emp.get("dob"),
        "telephone": emp.get("telephone"),
        "email": emp.get("email"),
        "invited_email": emp.get("invited_email"),
        "address1": emp.get("address1"),
        "postcode": emp.get("postcode"),
        "ni_number": emp.get("ni_number"),
        "emergency_contact_name": emergency.get("name"),
        "emergency_contact_phone": emergency.get("phone"),
        "emergency_contact_relationship": emergency.get("relationship"),
        "right_to_work_share_code": emp.get("right_to_work_share_code"),
        "dvla_check": emp.get("dvla_check"),
        # --- business
        "company_name": biz.get("company_name"),
        "bank_account": biz.get("bank_account"),
        "sort_code": biz.get("sort_code"),
        "utr": biz.get("utr"),
        "vat_number": biz.get("vat_number"),
        # --- insurance
        "insurance_option": emp.get("insurance_option"),
        # --- invoice service
        "invoice_service_requested": bool(emp.get("invoice_service_requested")),
        "invoice_service_charge": emp.get("invoice_service_charge"),
        "invoice_emails": emp.get("invoice_emails") or [],
        "invoice_email_1": emp.get("invoice_email_1"),
        "invoice_email_2": emp.get("invoice_email_2"),
        # --- medical (yes/no answers)
        **{f"medical_{k}": med.get(k) for k in _MEDICAL_KEYS},
        "medical_if_yes_details": med.get("if_yes_details"),
        "medical_medication_disability_details": med.get("medication_disability_details"),
        # --- havs
        **{f"havs_{k}": havs.get(k) for k in [
            "tingling_after_vibration", "tingling_other_times",
            "night_pain_tingling_numbness", "finger_numbness_after_vibration",
            "fingers_white_in_cold", "fingers_white_other_times",
            "muscle_or_joint_problems", "difficulty_handling_small_objects",
        ]},
        # --- signature & submission
        "digital_signature_name": emp.get("digital_signature_name"),
        "submitted_at": emp.get("submitted_at"),
        "access_code": emp.get("access_code"),
        # --- compliance acknowledgements (default false for legacy records)
        "health_safety_acknowledged": bool(emp.get("health_safety_acknowledged")),
        "health_safety_completed_at": emp.get("health_safety_completed_at"),
        "health_safety_sections": emp.get("health_safety_sections") or {},
        "site_rules_acknowledged": bool(emp.get("site_rules_acknowledged")),
        "site_rules_completed_at": emp.get("site_rules_completed_at"),
        # --- file URLs (the master HR record)
        "passport_url": url_of("passport"),
        "driving_licence_url": url_of("driving_licence"),
        "insurance_certificate_url": url_of("insurance_certificate"),
        "bank_proof_url": url_of("bank_proof"),
        "signature_url": url_of("signature"),
        "pdf_url": pdf_url,
        # --- HR workflow / status (review_status is set on first create only)
        "missing_documents": _compute_missing_documents(emp, files),
        "completed_modules": ["induction"],
        # --- derived statuses (HR-friendly, used by the admin portal + CSV)
        "induction_status": _compute_induction_status(
            _compute_missing_documents(emp, files), pdf_url
        ),
        "medical_status": _compute_medical_status(med),
        "passport_status": _doc_status(url_of("passport")),
        "driving_licence_status": _doc_status(url_of("driving_licence")),
        "bank_proof_status": _doc_status(url_of("bank_proof")),
        "insurance_certificate_status": _doc_status(url_of("insurance_certificate"))
            if (emp.get("insurance_option") or "").lower() == "own"
            else "N/A (covered by PNC)",
        # --- bookkeeping
        "summary_generated_at": now,
        "status": "completed",
    }
    return summary


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@api_router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "pnc-induction-api"}


# ---------------------------------------------------------------------------
# Public: validate an access code before letting the inductee enter the wizard.
# Server-side validation removes the need for Firebase Web SDK reads on
# `access_codes` and keeps every login attempt visible in Cloud Run logs.
# ---------------------------------------------------------------------------


class ValidateAccessCodeIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    code: str = Field(..., min_length=4, max_length=64)


@api_router.post("/validate-access-code")
async def validate_access_code(payload: ValidateAccessCodeIn) -> dict[str, Any]:
    from firebase_client import get_firestore
    from google.cloud.firestore_v1.base_query import FieldFilter

    code = (payload.code or "").strip().upper()
    email = (payload.email or "").strip().lower()
    if not code or not email:
        logger.info("validate.bad_input email_present=%s code_present=%s", bool(email), bool(code))
        return {"valid": False, "reason": "missing_fields"}

    db = get_firestore()
    project_id = getattr(db, "project", None) or "<unknown>"

    # Look up by code only — there is exactly one document per code (uniqueness
    # is enforced at invite creation time). Then verify email out-of-band.
    snaps = list(
        db.collection("access_codes")
          .where(filter=FieldFilter("code", "==", code))
          .limit(1)
          .stream()
    )
    if not snaps:
        logger.info(
            "validate.not_found project=%s collection=access_codes code=%s email=%s",
            project_id, code, email,
        )
        return {"valid": False, "reason": "not_recognised"}

    snap = snaps[0]
    data = snap.to_dict() or {}
    stored_email = (data.get("email") or "").strip().lower() or None

    if data.get("used"):
        logger.info(
            "validate.already_used project=%s doc_id=%s code=%s email=%s stored_email=%s",
            project_id, snap.id, code, email, stored_email,
        )
        return {"valid": False, "reason": "already_used"}

    if stored_email and stored_email != email:
        logger.info(
            "validate.email_mismatch project=%s doc_id=%s code=%s submitted_email=%s stored_email=%s",
            project_id, snap.id, code, email, stored_email,
        )
        return {"valid": False, "reason": "email_mismatch"}

    logger.info(
        "validate.ok project=%s doc_id=%s code=%s email=%s",
        project_id, snap.id, code, email,
    )
    return {
        "valid": True,
        "access_code_id": snap.id,
        "code": code,
        "email": stored_email or email,
        "full_name": data.get("full_name") or "",
    }


class MarkCodeUsedIn(BaseModel):
    access_code_id: str = Field(..., min_length=1, max_length=128)
    employee_id: str = Field(..., min_length=1, max_length=128)


@api_router.post("/access-code/mark-used")
async def mark_access_code_used(payload: MarkCodeUsedIn) -> dict[str, Any]:
    """Mark an access code as consumed after the inductee finalises the form.

    Idempotent: a second call for the same access_code_id is a no-op and
    still returns 200 — we never want a hiccup here to break the inductee's
    submit flow.
    """
    from firebase_client import get_firestore

    db = get_firestore()
    project_id = getattr(db, "project", None) or "<unknown>"
    access_code_id = payload.access_code_id.strip()
    employee_id = payload.employee_id.strip()

    ref = db.collection("access_codes").document(access_code_id)
    snap = ref.get()
    if not snap.exists:
        logger.warning(
            "mark_used.not_found project=%s collection=access_codes doc_id=%s employee_id=%s",
            project_id, access_code_id, employee_id,
        )
        raise HTTPException(status_code=404, detail="access_code_id not found")

    data = snap.to_dict() or {}
    already_used = bool(data.get("used"))

    try:
        ref.update({
            "used": True,
            "used_at": datetime.now(timezone.utc).isoformat(),
            "used_at_server": datetime.now(timezone.utc),
            "employee_id": employee_id,
        })
    except Exception as exc:  # noqa: BLE001 — surface every write failure
        logger.exception(
            "mark_used.write_failed project=%s doc_id=%s employee_id=%s err=%s",
            project_id, access_code_id, employee_id, exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to mark access code as used. Please retry.",
        )

    logger.info(
        "mark_used.ok project=%s doc_id=%s code=%s employee_id=%s previously_used=%s",
        project_id, access_code_id, data.get("code"), employee_id, already_used,
    )
    return {
        "ok": True,
        "access_code_id": access_code_id,
        "employee_id": employee_id,
        "code": data.get("code"),
        "previously_used": already_used,
    }


class FileUploadIn(BaseModel):
    path: str
    url: str | None = None
    name: str | None = None
    size: int | None = None
    type: str | None = None


class SubmitInductionIn(BaseModel):
    # Session linkage (from AccessGate -> sessionStorage)
    access_code_id: str = Field(..., min_length=1, max_length=128)
    access_code: str = Field(..., min_length=1, max_length=64)
    invited_email: str | None = Field(default=None, max_length=200)
    # Section 1 — personal
    full_name: str = Field(..., min_length=1, max_length=200)
    dob: str = Field(..., min_length=1, max_length=32)
    telephone: str = Field(..., min_length=1, max_length=32)
    email: str = Field(..., min_length=3, max_length=200)
    address1: str = Field(..., min_length=1, max_length=300)
    postcode: str = Field(..., min_length=1, max_length=20)
    ni_number: str = Field(..., min_length=1, max_length=20)
    emergency_name: str = Field(..., min_length=1, max_length=200)
    emergency_phone: str = Field(..., min_length=1, max_length=32)
    emergency_relationship: str = Field(..., min_length=1, max_length=80)
    right_to_work_share_code: str = Field(..., min_length=1, max_length=32)
    dvla_check: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    bank_account: str = Field(..., min_length=1, max_length=32)
    sort_code: str = Field(..., min_length=1, max_length=16)
    utr: str = Field(..., min_length=1, max_length=32)
    vat_number: str | None = Field(default=None, max_length=32)
    insurance_option: str = Field(..., min_length=1, max_length=20)
    invoice_service_requested: bool = Field(default=False)
    invoice_email_1: str | None = Field(default=None, max_length=200)
    invoice_email_2: str | None = Field(default=None, max_length=200)
    # Section 3 — signature (image already uploaded to Storage via `files.signature`)
    digital_signature_name: str = Field(..., min_length=1, max_length=200)
    # Section 2 — medical + HAVS answers (all yes/no)
    medical: dict[str, Any] = Field(default_factory=dict)
    havs: dict[str, Any] = Field(default_factory=dict)
    # Files already uploaded directly to Storage (slot -> {path, url, name, size, type})
    files: dict[str, FileUploadIn] = Field(default_factory=dict)
    # Canonical storage folder path (built client-side from slug + employee_id placeholder)
    storage_folder_path: str = Field(..., min_length=1, max_length=300)
    submitted_at: str = Field(..., min_length=1, max_length=40)
    # Compliance acknowledgements (mandatory)
    health_safety_acknowledged: bool = Field(default=False)
    health_safety_completed_at: str | None = Field(default=None, max_length=40)
    health_safety_sections: dict[str, str] = Field(default_factory=dict)
    site_rules_acknowledged: bool = Field(default=False)
    site_rules_completed_at: str | None = Field(default=None, max_length=40)


class SubmitInductionOut(BaseModel):
    employee_id: str
    pdf_url: str | None
    employee_summary_id: str
    submitted_at: str


@api_router.post("/induction/submit", response_model=SubmitInductionOut)
async def submit_induction(payload: SubmitInductionIn) -> SubmitInductionOut:
    """Single endpoint that performs the entire induction submit:
    1. Create employees doc
    2. Create medical_history doc
    3. Create havs_questionnaires doc
    4. Create employee_documents doc (files already in Storage)
    5. Mark access code as used
    6. Generate PDF + employee_summary

    All steps run server-side via the Firebase Admin SDK so security rules
    cannot block submission and every stage is logged in Cloud Run.
    """
    from firebase_client import get_bucket, get_firestore
    from pdf_generator import build_induction_pdf

    db = get_firestore()
    bucket = get_bucket()
    project_id = getattr(db, "project", None) or "<unknown>"
    server_now = datetime.now(timezone.utc)
    submitted_at = payload.submitted_at

    # Mandatory compliance gate — backend authoritative check.
    from compliance_content import HEALTH_SAFETY_KEYS
    missing_hs = [k for k in HEALTH_SAFETY_KEYS if not payload.health_safety_sections.get(k)]
    if missing_hs or not payload.health_safety_acknowledged or not payload.site_rules_acknowledged:
        logger.warning(
            "submit.compliance_blocked project=%s email=%s missing_hs=%s hs_ack=%s site_rules_ack=%s",
            project_id, payload.email, missing_hs,
            payload.health_safety_acknowledged, payload.site_rules_acknowledged,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "Please confirm that you have read and understood the Health & Safety "
                "information and Site Rules before submitting your induction."
            ),
        )

    logger.info(
        "submit.start project=%s access_code_id=%s code=%s email=%s",
        project_id, payload.access_code_id, payload.access_code, payload.email,
    )

    # Defensive initialisation — every real code path sets this in the
    # employees.add() try-block below, but declaring it here appeases static
    # analysers and guarantees the SubmitInductionOut construction at the
    # bottom of the function never trips on an unbound name.
    employee_id: str = ""

    # ---- Invoice-service validation (server-side authoritative) ----
    invoice_email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    invoice_emails_list: list[str] = []
    if payload.invoice_service_requested:
        raw_emails: list[str] = []
        if payload.invoice_email_1:
            raw_emails.append(payload.invoice_email_1)
        if payload.invoice_email_2:
            raw_emails.append(payload.invoice_email_2)
        # Trim, lowercase, dedupe (case-insensitive)
        seen: set[str] = set()
        invalid: list[str] = []
        for raw in raw_emails:
            e = (raw or "").strip().lower()
            if not e:
                continue
            if not invoice_email_re.fullmatch(e):
                invalid.append(raw)
                continue
            if e in seen:
                continue
            seen.add(e)
            invoice_emails_list.append(e)
        if invalid:
            logger.warning(
                "submit.invoice_invalid_email project=%s email=%s invalid=%s",
                project_id, payload.email, invalid,
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid invoice email address(es): {', '.join(invalid)}",
            )
        if len(invoice_emails_list) == 0:
            raise HTTPException(
                status_code=422,
                detail="At least one invoice email is required when the invoicing service is selected.",
            )
        if len(invoice_emails_list) > 2:
            raise HTTPException(
                status_code=422,
                detail="Maximum 2 invoice email addresses allowed.",
            )

    # 1. employees -------------------------------------------------------------
    employee_payload: dict[str, Any] = {
        "full_name": payload.full_name,
        "dob": payload.dob,
        "telephone": payload.telephone,
        "email": payload.email,
        "invited_email": payload.invited_email or payload.email,
        "address1": payload.address1,
        "postcode": payload.postcode,
        "ni_number": payload.ni_number,
        "emergency_contact": {
            "name": payload.emergency_name,
            "phone": payload.emergency_phone,
            "relationship": payload.emergency_relationship,
        },
        "right_to_work_share_code": payload.right_to_work_share_code,
        "dvla_check": payload.dvla_check,
        "business": {
            "company_name": payload.company_name,
            "bank_account": payload.bank_account,
            "sort_code": payload.sort_code,
            "utr": payload.utr,
            "vat_number": payload.vat_number or None,
        },
        "insurance_option": payload.insurance_option,
        "invoice_service_requested": payload.invoice_service_requested,
        "invoice_service_charge": 2 if payload.invoice_service_requested else None,
        "invoice_emails": invoice_emails_list,
        "invoice_email_1": invoice_emails_list[0] if len(invoice_emails_list) >= 1 else None,
        "invoice_email_2": invoice_emails_list[1] if len(invoice_emails_list) >= 2 else None,
        "digital_signature_name": payload.digital_signature_name,
        "access_code": payload.access_code,
        "access_code_id": payload.access_code_id,
        "submitted_at": submitted_at,
        "submitted_at_server": server_now,
        "status": "submitted",
        # Compliance acknowledgements
        "health_safety_acknowledged": True,
        "health_safety_completed_at": payload.health_safety_completed_at or server_now.isoformat(),
        "health_safety_sections": payload.health_safety_sections,
        "site_rules_acknowledged": True,
        "site_rules_completed_at": payload.site_rules_completed_at or server_now.isoformat(),
    }
    try:
        _, emp_ref = db.collection("employees").add(employee_payload)
        employee_id = emp_ref.id
        logger.info(
            "submit.employee_created project=%s employee_id=%s email=%s full_name=%r",
            project_id, employee_id, payload.email, payload.full_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("submit.employee_failed project=%s err=%s", project_id, exc)
        raise HTTPException(status_code=502, detail=f"Failed to create employee record: {exc}")

    # 2. medical_history -------------------------------------------------------
    medical_doc: dict[str, Any] = {
        "employee_id": employee_id,
        **{k: payload.medical.get(k) for k in _MEDICAL_KEYS},
        "if_yes_details": payload.medical.get("if_yes_details") or "",
        "medication_disability_details": payload.medical.get("medication_disability_details") or "",
        "submitted_at": submitted_at,
        "submitted_at_server": server_now,
    }
    try:
        db.collection("medical_history").add(medical_doc)
        logger.info("submit.medical_created project=%s employee_id=%s", project_id, employee_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("submit.medical_failed project=%s employee_id=%s err=%s",
                         project_id, employee_id, exc)
        raise HTTPException(status_code=502, detail=f"Failed to create medical record: {exc}")

    # 3. havs_questionnaires ---------------------------------------------------
    _HAVS_KEYS = [
        "tingling_after_vibration", "tingling_other_times",
        "night_pain_tingling_numbness", "finger_numbness_after_vibration",
        "fingers_white_in_cold", "fingers_white_other_times",
        "muscle_or_joint_problems", "difficulty_handling_small_objects",
    ]
    havs_doc: dict[str, Any] = {
        "employee_id": employee_id,
        **{k: payload.havs.get(k) for k in _HAVS_KEYS},
        "submitted_at": submitted_at,
        "submitted_at_server": server_now,
    }
    try:
        db.collection("havs_questionnaires").add(havs_doc)
        logger.info("submit.havs_created project=%s employee_id=%s", project_id, employee_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("submit.havs_failed project=%s employee_id=%s err=%s",
                         project_id, employee_id, exc)
        raise HTTPException(status_code=502, detail=f"Failed to create HAVS record: {exc}")

    # 4. employee_documents ----------------------------------------------------
    # For each uploaded file we ensure a download-token URL exists. The
    # frontend now uploads bytes to Storage but does not call getDownloadURL
    # (which requires a permissive read rule) \u2014 the Admin SDK mints the token
    # here instead. If the frontend supplied a URL (legacy path), we keep it.
    files_meta: dict[str, Any] = {}
    for slot, f in payload.files.items():
        file_dict = f.model_dump()
        if not file_dict.get("url") and file_dict.get("path"):
            try:
                blob = bucket.blob(file_dict["path"])
                if blob.exists():
                    file_dict["url"] = _make_public_url(bucket, blob)
                else:
                    logger.warning(
                        "submit.file_missing_in_storage project=%s slot=%s path=%s",
                        project_id, slot, file_dict["path"],
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "submit.file_url_mint_failed project=%s slot=%s path=%s err=%s",
                    project_id, slot, file_dict.get("path"), exc,
                )
        files_meta[slot] = file_dict
    documents_doc: dict[str, Any] = {
        "employee_id": employee_id,
        "storage_folder_path": payload.storage_folder_path,
        "files": files_meta,
        "pdf_url": None,
        "submitted_at": submitted_at,
        "submitted_at_server": server_now,
    }
    try:
        db.collection("employee_documents").add(documents_doc)
        logger.info(
            "submit.documents_created project=%s employee_id=%s slots=%s",
            project_id, employee_id, sorted(files_meta.keys()),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("submit.documents_failed project=%s employee_id=%s err=%s",
                         project_id, employee_id, exc)
        raise HTTPException(status_code=502, detail=f"Failed to create documents record: {exc}")

    # 5. Mark access code as used (inline; same idempotent logic as /access-code/mark-used)
    try:
        code_ref = db.collection("access_codes").document(payload.access_code_id)
        code_snap = code_ref.get()
        if code_snap.exists:
            code_ref.update({
                "used": True,
                "used_at": datetime.now(timezone.utc).isoformat(),
                "used_at_server": datetime.now(timezone.utc),
                "employee_id": employee_id,
            })
            logger.info(
                "mark_used.ok project=%s doc_id=%s code=%s employee_id=%s previously_used=%s",
                project_id, payload.access_code_id, payload.access_code,
                employee_id, bool(code_snap.to_dict().get("used")),
            )
        else:
            logger.warning(
                "mark_used.skipped_missing_doc project=%s doc_id=%s code=%s employee_id=%s",
                project_id, payload.access_code_id, payload.access_code, employee_id,
            )
    except Exception as exc:  # noqa: BLE001
        # Mark-used failure must not block submission — log loudly and continue.
        logger.exception(
            "mark_used.failed_non_blocking project=%s doc_id=%s employee_id=%s err=%s",
            project_id, payload.access_code_id, employee_id, exc,
        )

    # 6. PDF generation + employee_summary -------------------------------------
    pdf_url: str | None = None
    try:
        bundle = _fetch_employee_bundle(db, employee_id)
        documents_meta = dict(bundle["documents"] or {})
        files = documents_meta.get("files") or {}
        storage_folder_path, is_legacy = _resolve_storage_folder(
            documents_meta, bundle["employee"], employee_id
        )

        sig_bytes = _download_signature_bytes(bucket, files)
        if sig_bytes:
            documents_meta["signature_image_bytes"] = sig_bytes

        submitted_at_dt = None
        try:
            submitted_at_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            submitted_at_dt = None

        pdf_bytes = build_induction_pdf(
            employee_id=employee_id,
            employee=bundle["employee"],
            medical=bundle["medical"],
            havs=bundle["havs"],
            documents_meta=documents_meta,
            submitted_at=submitted_at_dt,
        )
        pdf_path = f"{storage_folder_path}pdf/induction-{employee_id}.pdf"
        blob = bucket.blob(pdf_path)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        pdf_url = _make_public_url(bucket, blob)

        # Stamp the PDF URL onto employee_documents
        docs_doc_id = (bundle["documents"] or {}).get("__doc_id__")
        if docs_doc_id:
            db.collection("employee_documents").document(docs_doc_id).update({
                "pdf_url": pdf_url,
                "pdf_path": pdf_path,
                "pdf_generated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Create employee_summary (HR master record)
        summary = _flatten_for_summary(bundle, pdf_url, employee_id, storage_folder_path)
        summary_ref = db.collection("employee_summary").document(employee_id)
        existing_summary = summary_ref.get()
        if not existing_summary.exists or not (existing_summary.to_dict() or {}).get("review_status"):
            summary["review_status"] = "pending_review"
        summary_ref.set(summary, merge=True)
        logger.info(
            "submit.pdf_generated project=%s employee_id=%s pdf_path=%s",
            project_id, employee_id, pdf_path,
        )
    except Exception as exc:  # noqa: BLE001
        # PDF failure is non-fatal: HR can regenerate later via /api/induction/finalize.
        # Submission itself succeeded — we logged each created doc above.
        logger.exception(
            "submit.pdf_failed_non_blocking project=%s employee_id=%s err=%s",
            project_id, employee_id, exc,
        )

    logger.info(
        "submit.complete project=%s employee_id=%s pdf_url_present=%s",
        project_id, employee_id, bool(pdf_url),
    )
    return SubmitInductionOut(
        employee_id=employee_id,
        pdf_url=pdf_url,
        employee_summary_id=employee_id,
        submitted_at=submitted_at,
    )


@api_router.post("/induction/finalize", response_model=FinalizeOut)
async def finalize_induction(payload: FinalizeIn) -> FinalizeOut:
    # Import lazily so the module can load even without the SDK config (for tests).
    from firebase_client import get_bucket, get_firestore
    from pdf_generator import build_induction_pdf

    employee_id = payload.employee_id.strip()
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required")

    db = get_firestore()
    bucket = get_bucket()

    bundle = _fetch_employee_bundle(db, employee_id)
    documents_meta = dict(bundle["documents"] or {})
    files = documents_meta.get("files") or {}

    # Decide which Storage folder to use (explicit on new submissions, legacy for old).
    storage_folder_path, is_legacy = _resolve_storage_folder(
        documents_meta, bundle["employee"], employee_id
    )

    # Best-effort: load the drawn signature so it can be embedded in the PDF.
    sig_bytes = _download_signature_bytes(bucket, files)
    if sig_bytes:
        documents_meta["signature_image_bytes"] = sig_bytes

    submitted_iso = bundle["employee"].get("submitted_at")
    submitted_at = None
    if submitted_iso:
        try:
            submitted_at = datetime.fromisoformat(submitted_iso.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            submitted_at = None

    pdf_bytes = build_induction_pdf(
        employee_id=employee_id,
        employee=bundle["employee"],
        medical=bundle["medical"],
        havs=bundle["havs"],
        documents_meta=documents_meta,
        submitted_at=submitted_at,
    )

    # PDF goes inside the resolved Storage folder so it's grouped with the
    # employee's other documents. Legacy records (no storage_folder_path) fall
    # back to employees/{id}/pdf/ via _resolve_storage_folder.
    pdf_path = f"{storage_folder_path}pdf/induction-{employee_id}.pdf"
    blob = bucket.blob(pdf_path)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")
    pdf_url = _make_public_url(bucket, blob)

    # Update employee_documents.pdf_url for the existing record.
    # For legacy records (created before the folder-naming change) we do NOT
    # write storage_folder_path back — they keep their original shape.
    docs_doc_id = (bundle["documents"] or {}).get("__doc_id__")
    update_payload: dict[str, Any] = {
        "pdf_url": pdf_url,
        "pdf_path": pdf_path,
        "pdf_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not is_legacy:
        update_payload["storage_folder_path"] = storage_folder_path

    if docs_doc_id:
        db.collection("employee_documents").document(docs_doc_id).update(update_payload)
    else:
        # Create one if it doesn't exist yet (should not normally happen)
        new_doc: dict[str, Any] = {
            "employee_id": employee_id,
            "files": {},
            **update_payload,
        }
        if not is_legacy:
            new_doc["storage_folder_path"] = storage_folder_path
        db.collection("employee_documents").add(new_doc)

    # Create / overwrite the denormalised master HR record
    summary = _flatten_for_summary(bundle, pdf_url, employee_id, storage_folder_path)
    if is_legacy:
        # Legacy records have no canonical folder path — leave the field empty
        # in the summary so HR can tell them apart from new submissions.
        summary["storage_folder_path"] = None
    summary_ref = db.collection("employee_summary").document(employee_id)
    existing_summary = summary_ref.get()
    if not existing_summary.exists or not (existing_summary.to_dict() or {}).get("review_status"):
        # Set the HR-workflow status only on first creation so we don't overwrite
        # an admin's later approval/rejection on re-finalize.
        summary["review_status"] = "pending_review"
    # Use employee_id as the doc ID so it's idempotent and easy to look up
    summary_ref.set(summary, merge=True)

    return FinalizeOut(
        employee_id=employee_id,
        pdf_url=pdf_url,
        employee_summary_id=employee_id,
        generated_at=summary["summary_generated_at"],
    )


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

app.include_router(api_router)
from admin_routes import admin_router  # noqa: E402
app.include_router(admin_router)

# CORS \u2014 strict allow-list from env. Never allow `*` when credentials are on.
_raw_origins = os.environ.get("CORS_ORIGINS", "").strip()
_allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] if _raw_origins else []
if not _allow_origins:
    # Safety fallback \u2014 refuse cross-origin traffic if no origins are configured.
    _allow_origins = ["null"]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allow_origins,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)
