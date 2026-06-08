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


def _flatten_for_summary(bundle: dict, pdf_url: str, employee_id: str) -> dict[str, Any]:
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
        **{f"medical_{k}": med.get(k) for k in [
            "receiving_treatment", "prescribed_medication", "medical_warning_card",
            "pregnant", "allergies", "asthma_bronchitis_chest",
            "fainting_blackouts_epilepsy", "heart_problems", "diabetes",
            "bone_or_joint_disease", "skin_disease", "persistent_bleeding_bruising",
            "liver_or_kidney_disease", "havs_or_cts", "other_serious_illness",
        ]},
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

    pdf_path = f"employees/{employee_id}/pdf/induction-{employee_id}.pdf"
    blob = bucket.blob(pdf_path)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")
    pdf_url = _make_public_url(bucket, blob)

    # Update employee_documents.pdf_url for the existing record
    docs_doc_id = (bundle["documents"] or {}).get("__doc_id__")
    if docs_doc_id:
        db.collection("employee_documents").document(docs_doc_id).update(
            {"pdf_url": pdf_url, "pdf_path": pdf_path, "pdf_generated_at": datetime.now(timezone.utc).isoformat()}
        )
    else:
        # Create one if it doesn't exist yet (should not normally happen)
        db.collection("employee_documents").add(
            {
                "employee_id": employee_id,
                "files": {},
                "pdf_url": pdf_url,
                "pdf_path": pdf_path,
                "pdf_generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Create / overwrite the denormalised master HR record
    summary = _flatten_for_summary(bundle, pdf_url, employee_id)
    # Use employee_id as the doc ID so it's idempotent and easy to look up
    db.collection("employee_summary").document(employee_id).set(summary, merge=True)

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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
