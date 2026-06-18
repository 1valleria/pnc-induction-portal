"""End-to-end test for multi-recipient manager email notifications.

Creates a real induction record, then exercises:
  - 0 manager emails (no notification, status absent)
  - 1 manager email
  - 2 manager emails
  - 3 manager emails
  - Comma+space variations + duplicates + empty entries
  - Backwards-compat: existing record with single manager_email string
  - Invalid email rejected
"""
from __future__ import annotations

import base64
import json
import os
import sys

import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv("/app/backend/.env")

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

print(f"API: {API}")
print(f"Project: {sa['project_id']}")
print("=" * 80)


def create_test_record(name: str = "Multi Manager Test"):
    """Create an inductee record via the regular submit endpoint."""
    inv = requests.post(
        f"{API}/api/admin/invites",
        auth=(ADMIN_USER, ADMIN_PASS),
        json={"full_name": name, "email": f"test-{os.urandom(3).hex()}@example.com", "send_email": False},
        timeout=30,
    ).json()
    val = requests.post(
        f"{API}/api/validate-access-code",
        json={"email": "ignored", "code": inv["code"]},
        timeout=30,
    )
    # Code lookup ignores email when stored email is null; but invites do set email -> fetch directly
    code_doc = next(db.collection("access_codes").where("code", "==", inv["code"]).stream())
    employee_email = (code_doc.to_dict() or {}).get("email")
    val = requests.post(
        f"{API}/api/validate-access-code",
        json={"email": employee_email, "code": inv["code"]},
        timeout=30,
    ).json()
    sub = requests.post(
        f"{API}/api/induction/submit",
        json={
            "access_code_id": val["access_code_id"],
            "access_code": inv["code"],
            "invited_email": employee_email,
            "full_name": name,
            "dob": "1990-01-01", "telephone": "07700900000", "email": employee_email,
            "address1": "1 Test St", "postcode": "SW1A 1AA", "ni_number": "QQ123456C",
            "emergency_name": "Kin", "emergency_phone": "07700900000", "emergency_relationship": "Spouse",
            "right_to_work_share_code": "ABC", "dvla_check": "yes",
            "company_name": "Test Ltd", "bank_account": "12345678", "sort_code": "12-34-56",
            "utr": "1234567890", "vat_number": None,
            "insurance_option": "covered_by_pnc", "digital_signature_name": name,
            "medical": {}, "havs": {},
            "files": {},
            "storage_folder_path": f"employees/multimgr-{val['access_code_id']}/",
            "submitted_at": "2026-06-14T13:00:00.000Z",
        }, timeout=60,
    ).json()
    return sub["employee_id"], val["access_code_id"]


def review(employee_id: str, status: str, manager_email: str | None = None, note: str | None = None):
    body = {"review_status": status}
    if manager_email is not None:
        body["manager_email"] = manager_email
    if note:
        body["review_note"] = note
    return requests.patch(
        f"{API}/api/admin/employees/{employee_id}/review",
        auth=(ADMIN_USER, ADMIN_PASS),
        json=body, timeout=30,
    )


def cleanup(employee_id: str, access_code_id: str):
    for col in ("medical_history", "havs_questionnaires", "employee_documents"):
        for d in db.collection(col).where("employee_id", "==", employee_id).stream():
            d.reference.delete()
    db.collection("employees").document(employee_id).delete()
    db.collection("employee_summary").document(employee_id).delete()
    if access_code_id:
        db.collection("access_codes").document(access_code_id).delete()


results = []

def check(name: str, condition, detail: str = ""):
    ok = bool(condition)
    print(f"   {'PASS' if ok else 'FAIL'}: {name}{(' — ' + detail) if detail else ''}")
    results.append((name, ok))


# ---------------------------------------------------------------------------
# Test 1 — single manager email
# ---------------------------------------------------------------------------
print("[1] approve + single manager email")
emp_id, ac_id = create_test_record("Single Mgr Test")
r = review(emp_id, "approved", "manager1@company.com")
assert r.status_code == 200, r.text
data = r.json()
check("status 200", r.status_code == 200)
check("manager_emails list = 1", data.get("manager_emails") == ["manager1@company.com"])
check("manager_email string preserved", data.get("manager_email") == "manager1@company.com")
check("manager_email_status set", data.get("manager_email_status") in {"sent", "failed", "partial"})
# Firestore persistence check
fs = db.collection("employee_summary").document(emp_id).get().to_dict()
check("Firestore manager_emails array", fs.get("manager_emails") == ["manager1@company.com"])
check("Firestore manager_email string", fs.get("manager_email") == "manager1@company.com")
cleanup(emp_id, ac_id)

# ---------------------------------------------------------------------------
# Test 2 — two emails
# ---------------------------------------------------------------------------
print("[2] approve + 2 manager emails (comma)")
emp_id, ac_id = create_test_record("Two Mgrs Test")
r = review(emp_id, "approved", "m1@c.com, m2@c.com")
data = r.json()
check("status 200", r.status_code == 200)
check("manager_emails = ['m1@c.com','m2@c.com']", data.get("manager_emails") == ["m1@c.com", "m2@c.com"])
check("manager_email joined", data.get("manager_email") == "m1@c.com, m2@c.com")
fs = db.collection("employee_summary").document(emp_id).get().to_dict()
check("Firestore array len 2", len(fs.get("manager_emails") or []) == 2)
cleanup(emp_id, ac_id)

# ---------------------------------------------------------------------------
# Test 3 — three+ emails, mixed delimiters, duplicates, empties
# ---------------------------------------------------------------------------
print("[3] reject + 3 emails with whitespace, duplicates, empty entries")
emp_id, ac_id = create_test_record("Three Mgrs Test")
r = review(emp_id, "rejected", "  ceo@x.com,, ops@x.com ;hr@x.com,, CEO@x.com ", note="needs work")
data = r.json()
check("status 200", r.status_code == 200)
check("deduped + normalised", data.get("manager_emails") == ["ceo@x.com", "ops@x.com", "hr@x.com"])
check("manager_email joined", data.get("manager_email") == "ceo@x.com, ops@x.com, hr@x.com")
check("new_access_code present", bool(data.get("new_access_code")))
fs = db.collection("employee_summary").document(emp_id).get().to_dict()
check("Firestore array len 3", len(fs.get("manager_emails") or []) == 3)
cleanup(emp_id, ac_id)
# Cleanup the rejection-fresh access code too
new_code = data.get("new_access_code")
if new_code:
    for d in db.collection("access_codes").where("code", "==", new_code).stream():
        d.reference.delete()

# ---------------------------------------------------------------------------
# Test 4 — invalid email rejected with HTTP 422 listing offenders
# ---------------------------------------------------------------------------
print("[4] approve + invalid email -> HTTP 422")
emp_id, ac_id = create_test_record("Invalid Mgr Test")
r = review(emp_id, "approved", "good@c.com, not-an-email, also-bad")
check("status 422", r.status_code == 422)
check("detail mentions both invalids", "not-an-email" in r.text and "also-bad" in r.text)
# State should NOT have moved
fs = db.collection("employee_summary").document(emp_id).get().to_dict()
check("review_status untouched", fs.get("review_status") == "pending_review")
cleanup(emp_id, ac_id)

# ---------------------------------------------------------------------------
# Test 5 — Backwards compat: legacy doc with manager_email string only
# ---------------------------------------------------------------------------
print("[5] backwards compat — legacy record with manager_email string only")
emp_id, ac_id = create_test_record("Legacy Mgr Test")
# Simulate a legacy record state: only manager_email string, no array
db.collection("employee_summary").document(emp_id).update({
    "manager_email": "legacy-mgr@old.com",
    # NO manager_emails field
})
# Re-review (approve again) — should accept and not crash
r = review(emp_id, "approved", "legacy-mgr@old.com")
data = r.json()
check("legacy record approve OK", r.status_code == 200)
check("now has manager_emails array", data.get("manager_emails") == ["legacy-mgr@old.com"])
# A read with no review action at all should still work for the API listing
listing = requests.get(f"{API}/api/admin/employees", auth=(ADMIN_USER, ADMIN_PASS), timeout=30).json()
found = [it for it in listing.get("items", []) if it.get("employee_id") == emp_id]
check("appears in admin list", bool(found))
cleanup(emp_id, ac_id)

# ---------------------------------------------------------------------------
# Test 6 — no manager email
# ---------------------------------------------------------------------------
print("[6] approve with NO manager email (existing flow)")
emp_id, ac_id = create_test_record("No Mgr Test")
r = review(emp_id, "approved", None)
data = r.json()
check("status 200", r.status_code == 200)
check("manager_emails absent or empty", not data.get("manager_emails"))
check("manager_email_status absent", "manager_email_status" not in data or data["manager_email_status"] is None)
cleanup(emp_id, ac_id)

print("=" * 80)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
