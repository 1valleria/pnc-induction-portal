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


app = FastAPI(title="PNC Induction Portal API")
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
