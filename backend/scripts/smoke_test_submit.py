"""End-to-end smoke test of POST /api/induction/submit.

Creates a fresh access code, validates it, then submits a complete induction
payload (without real file uploads — we use placeholder URLs). Verifies every
Firestore collection was written and the access code was marked used.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv("/app/backend/.env")
API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
# Read it from frontend/.env if not set in backend/.env
if "REACT_APP_BACKEND_URL" not in os.environ:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                API = line.split("=", 1)[1].strip()
                break

ADMIN_USER = os.environ["ADMIN_USERNAME"]
ADMIN_PASS = os.environ["ADMIN_PASSWORD"]

sa = json.loads(base64.b64decode(os.environ["FIREBASE_SERVICE_ACCOUNT_B64"]))
firebase_admin.initialize_app(credentials.Certificate(sa))
db = firestore.client()

EMAIL = "submit-smoke-test@example.com"
print(f"Project: {sa['project_id']}")
print(f"API:     {API}")
print("=" * 80)

# 1. Create invite via admin endpoint
print("[1] POST /api/admin/invites")
r = requests.post(
    f"{API}/api/admin/invites",
    auth=(ADMIN_USER, ADMIN_PASS),
    json={"full_name": "Submit Smoke Test", "email": EMAIL, "send_email": False},
    timeout=30,
)
assert r.status_code == 200, (r.status_code, r.text)
invite = r.json()
print(f"    code={invite['code']}  id={invite['id']}")

# 2. Validate the access code
print("[2] POST /api/validate-access-code")
r = requests.post(
    f"{API}/api/validate-access-code",
    json={"email": EMAIL, "code": invite["code"]},
    timeout=30,
)
assert r.status_code == 200 and r.json().get("valid") is True, (r.status_code, r.text)
access_code_id = r.json()["access_code_id"]
print(f"    valid=True  access_code_id={access_code_id}")

# 3. Submit induction
print("[3] POST /api/induction/submit")
payload = {
    "access_code_id": access_code_id,
    "access_code": invite["code"],
    "invited_email": EMAIL,
    "full_name": "Submit Smoke Test",
    "dob": "1990-01-01",
    "telephone": "07700900123",
    "email": EMAIL,
    "address1": "1 Test Street",
    "postcode": "SW1A 1AA",
    "ni_number": "QQ123456C",
    "emergency_name": "Next Of Kin",
    "emergency_phone": "07700900999",
    "emergency_relationship": "Spouse",
    "right_to_work_share_code": "ABC-DEF-GHI",
    "dvla_check": "yes",
    "company_name": "Smoke Test Ltd",
    "bank_account": "12345678",
    "sort_code": "12-34-56",
    "utr": "1234567890",
    "vat_number": None,
    "insurance_option": "covered_by_pnc",
    "digital_signature_name": "Submit Smoke Test",
    "medical": {
        "receiving_treatment": "no", "prescribed_medication": "no", "medical_warning_card": "no",
        "pregnant": "no", "allergies": "no", "asthma_bronchitis_chest": "no",
        "fainting_blackouts_epilepsy": "no", "heart_problems": "no", "diabetes": "no",
        "bone_or_joint_disease": "no", "skin_disease": "no", "persistent_bleeding_bruising": "no",
        "liver_or_kidney_disease": "no", "havs_or_cts": "no", "other_serious_illness": "no",
        "if_yes_details": "", "medication_disability_details": "",
    },
    "havs": {
        "tingling_after_vibration": "no", "tingling_other_times": "no",
        "night_pain_tingling_numbness": "no", "finger_numbness_after_vibration": "no",
        "fingers_white_in_cold": "no", "fingers_white_other_times": "no",
        "muscle_or_joint_problems": "no", "difficulty_handling_small_objects": "no",
    },
    "files": {
        # Placeholder URLs — real flow uploads to Storage first. PDF gen will
        # log a warning about missing signature bytes but submission still succeeds.
        "passport": {"path": f"employees/smoke-{access_code_id}/passport/p.jpg", "url": "https://example.com/p", "name": "p.jpg", "size": 1234, "type": "image/jpeg"},
        "driving_licence": {"path": f"employees/smoke-{access_code_id}/driving_licence/dl.jpg", "url": "https://example.com/dl", "name": "dl.jpg", "size": 1234, "type": "image/jpeg"},
        "bank_proof": {"path": f"employees/smoke-{access_code_id}/bank_proof/b.pdf", "url": "https://example.com/b", "name": "b.pdf", "size": 1234, "type": "application/pdf"},
        "signature": {"path": f"employees/smoke-{access_code_id}/signature/sig.png", "url": "https://example.com/sig", "name": "sig.png", "size": 1234, "type": "image/png"},
    },
    "storage_folder_path": f"employees/submit-smoke-test-{access_code_id}/",
    "submitted_at": "2026-06-14T13:00:00.000Z",
}
r = requests.post(f"{API}/api/induction/submit", json=payload, timeout=60)
assert r.status_code == 200, (r.status_code, r.text)
result = r.json()
print(f"    employee_id={result['employee_id']}  pdf_url_present={bool(result.get('pdf_url'))}")
employee_id = result["employee_id"]

# 4. Verify every collection has the doc
print("[4] Verifying Firestore writes...")
checks = {
    "employees": db.collection("employees").document(employee_id).get().exists,
    "medical_history": any(d.id for d in db.collection("medical_history").where(filter=firestore.firestore.FieldFilter("employee_id", "==", employee_id)).limit(1).stream())
        if hasattr(firestore.firestore, "FieldFilter")
        else any(True for _ in db.collection("medical_history").where("employee_id", "==", employee_id).limit(1).stream()),
    "havs_questionnaires": any(True for _ in db.collection("havs_questionnaires").where("employee_id", "==", employee_id).limit(1).stream()),
    "employee_documents": any(True for _ in db.collection("employee_documents").where("employee_id", "==", employee_id).limit(1).stream()),
    "employee_summary": db.collection("employee_summary").document(employee_id).get().exists,
}
for k, v in checks.items():
    print(f"    {k:<25} present = {v}")
all_ok = all(checks.values())

# 5. Check access_code marked as used
code_after = db.collection("access_codes").document(access_code_id).get().to_dict()
print(f"    access_codes.used        = {code_after.get('used')}  employee_id={code_after.get('employee_id')!r}")
mark_used_ok = code_after.get("used") is True and code_after.get("employee_id") == employee_id

# 6. CLEANUP — remove everything we just created
print("[5] Cleanup")
db.collection("employees").document(employee_id).delete()
for col in ("medical_history", "havs_questionnaires", "employee_documents"):
    for d in db.collection(col).where("employee_id", "==", employee_id).stream():
        d.reference.delete()
db.collection("employee_summary").document(employee_id).delete()
db.collection("access_codes").document(access_code_id).delete()
print("    deleted")

print("=" * 80)
print(f"RESULT: collections_ok={all_ok}  mark_used_ok={mark_used_ok}")
sys.exit(0 if (all_ok and mark_used_ok) else 1)
