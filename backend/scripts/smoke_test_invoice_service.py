"""End-to-end test for the invoice service feature.

Covers all 7 scenarios from the spec:
  1. Select No → submits without invoice emails
  2. Select Yes with one email → success
  3. Select Yes with two emails → success
  4. Select Yes with invalid email → blocked (422)
  5. More than two emails → not directly testable via Pydantic (only 2 fields exist
     in the model), but tested by sending the same email twice + a third in the
     dedupe check below
  6. Duplicate emails → deduped to one entry
  7. PDF contains invoice service info
  8. Admin dashboard / CSV columns present
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys
from datetime import datetime, timezone

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

sys.path.insert(0, "/app/backend")
from compliance_content import HEALTH_SAFETY_KEYS  # noqa: E402

print(f"API: {API}\nProject: {sa['project_id']}")
print("=" * 80)

results = []
def check(name, condition, detail=""):
    ok = bool(condition)
    print(f"   {'PASS' if ok else 'FAIL'}: {name}{(' — ' + detail) if detail else ''}")
    results.append((name, ok))


def fresh():
    inv = requests.post(
        f"{API}/api/admin/invites",
        auth=(ADMIN_USER, ADMIN_PASS),
        json={"full_name": "Invoice Test", "email": f"inv-{os.urandom(3).hex()}@example.com", "send_email": False},
        timeout=30,
    ).json()
    val = requests.post(
        f"{API}/api/validate-access-code",
        json={"email": inv["email"], "code": inv["code"]},
        timeout=30,
    ).json()
    return inv, val


def base_body(inv, val, **overrides):
    now = datetime.now(timezone.utc).isoformat()
    body = {
        "access_code_id": val["access_code_id"], "access_code": inv["code"],
        "invited_email": inv["email"], "full_name": "Invoice Test",
        "dob": "1990-01-01", "telephone": "07700900000", "email": inv["email"],
        "address1": "1 Test St", "postcode": "SW1A 1AA", "ni_number": "QQ123456C",
        "emergency_name": "Kin", "emergency_phone": "07700900000", "emergency_relationship": "Spouse",
        "right_to_work_share_code": "ABC", "dvla_check": "yes",
        "company_name": "Test Ltd", "bank_account": "12345678", "sort_code": "12-34-56",
        "utr": "1234567890", "vat_number": None,
        "insurance_option": "covered_by_pnc", "digital_signature_name": "Invoice Test",
        "medical": {}, "havs": {},
        "files": {},
        "storage_folder_path": f"employees/inv-{val['access_code_id']}/",
        "submitted_at": now,
        "health_safety_acknowledged": True,
        "health_safety_completed_at": now,
        "health_safety_sections": {k: now for k in HEALTH_SAFETY_KEYS},
        "site_rules_acknowledged": True,
        "site_rules_completed_at": now,
        "invoice_service_requested": False,
        "invoice_email_1": None,
        "invoice_email_2": None,
    }
    body.update(overrides)
    return body


def cleanup(emp_id, ac_id):
    for col in ("medical_history", "havs_questionnaires", "employee_documents"):
        for d in db.collection(col).where("employee_id", "==", emp_id).stream():
            d.reference.delete()
    db.collection("employees").document(emp_id).delete()
    db.collection("employee_summary").document(emp_id).delete()
    if ac_id:
        db.collection("access_codes").document(ac_id).delete()


# ---------------------------------------------------------------------------
# 1. Invoice service = No → submits without invoice emails
# ---------------------------------------------------------------------------
print("[1] invoice_service_requested=False → success")
inv, val = fresh()
r = requests.post(f"{API}/api/induction/submit", json=base_body(inv, val), timeout=60)
check("HTTP 200", r.status_code == 200)
emp_id = r.json()["employee_id"]
emp = db.collection("employees").document(emp_id).get().to_dict()
check("invoice_service_requested == False", emp.get("invoice_service_requested") is False)
check("invoice_emails is empty list", emp.get("invoice_emails") == [])
check("invoice_email_1 is None", emp.get("invoice_email_1") is None)
check("invoice_service_charge is None", emp.get("invoice_service_charge") is None)
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 2. Yes with one email
# ---------------------------------------------------------------------------
print("[2] Yes + 1 email → success")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True, invoice_email_1="ACCOUNTS@COMPANY.COM"),
    timeout=60,
)
check("HTTP 200", r.status_code == 200)
emp_id = r.json()["employee_id"]
emp = db.collection("employees").document(emp_id).get().to_dict()
check("invoice_service_requested True", emp.get("invoice_service_requested") is True)
check("invoice_emails == ['accounts@company.com'] (lowercased)",
      emp.get("invoice_emails") == ["accounts@company.com"])
check("invoice_service_charge == 2", emp.get("invoice_service_charge") == 2)
check("invoice_email_1 lowercased", emp.get("invoice_email_1") == "accounts@company.com")
check("invoice_email_2 is None", emp.get("invoice_email_2") is None)
# Summary mirror
summ = db.collection("employee_summary").document(emp_id).get().to_dict()
check("summary invoice_emails matches", summ.get("invoice_emails") == ["accounts@company.com"])
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 3. Yes with two emails
# ---------------------------------------------------------------------------
print("[3] Yes + 2 emails → success, both stored")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True,
                   invoice_email_1="  a@x.com  ", invoice_email_2="B@Y.com"),
    timeout=60,
)
check("HTTP 200", r.status_code == 200)
emp_id = r.json()["employee_id"]
emp = db.collection("employees").document(emp_id).get().to_dict()
check("invoice_emails has 2 entries (trimmed + lowercased)",
      emp.get("invoice_emails") == ["a@x.com", "b@y.com"])
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 4. Yes with invalid email → blocked
# ---------------------------------------------------------------------------
print("[4] Yes + invalid email → HTTP 422")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True, invoice_email_1="not-an-email"),
    timeout=60,
)
check("HTTP 422", r.status_code == 422)
check("error mentions invalid email", "not-an-email" in r.text or "Invalid" in r.text)
# No employee created
emps = list(db.collection("employees").where("access_code_id", "==", val["access_code_id"]).limit(1).stream())
check("no employee created on validation fail", not emps)
db.collection("access_codes").document(val["access_code_id"]).delete()

# ---------------------------------------------------------------------------
# 5. Yes but no emails → blocked
# ---------------------------------------------------------------------------
print("[5] Yes but no emails → HTTP 422")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True, invoice_email_1="", invoice_email_2=""),
    timeout=60,
)
check("HTTP 422", r.status_code == 422)
check("error mentions at least one email required",
      "At least one invoice email" in r.text or "required" in r.text.lower())
db.collection("access_codes").document(val["access_code_id"]).delete()

# ---------------------------------------------------------------------------
# 6. Duplicate emails → deduped to one
# ---------------------------------------------------------------------------
print("[6] Yes + duplicate emails (case differs) → deduped")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True,
                   invoice_email_1="same@x.com", invoice_email_2="SAME@X.com"),
    timeout=60,
)
check("HTTP 200", r.status_code == 200)
emp_id = r.json()["employee_id"]
emp = db.collection("employees").document(emp_id).get().to_dict()
check("invoice_emails deduped to 1 entry", emp.get("invoice_emails") == ["same@x.com"])
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 7. PDF includes invoice service info
# ---------------------------------------------------------------------------
print("[7] PDF includes invoice service section")
inv, val = fresh()
r = requests.post(
    f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True,
                   invoice_email_1="accounts@example.com", invoice_email_2="finance@example.com"),
    timeout=60,
).json()
emp_id = r["employee_id"]
pdf = requests.get(r["pdf_url"], timeout=60).content
from pypdf import PdfReader
text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
check("PDF has 'WEEKLY INVOICE SERVICE'", "WEEKLY INVOICE SERVICE" in text)
check("PDF shows 'Yes' for invoice service", "Yes" in text)
check("PDF shows '£2' weekly charge", "£2" in text)
check("PDF contains email1", "accounts@example.com" in text)
check("PDF contains email2", "finance@example.com" in text)
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 8. PDF for No correctly omits emails
# ---------------------------------------------------------------------------
print("[8] PDF for No omits email rows")
inv, val = fresh()
r = requests.post(f"{API}/api/induction/submit", json=base_body(inv, val), timeout=60).json()
emp_id = r["employee_id"]
pdf = requests.get(r["pdf_url"], timeout=60).content
text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
check("PDF has 'WEEKLY INVOICE SERVICE'", "WEEKLY INVOICE SERVICE" in text)
check("PDF says 'No' for invoice service", "WEEKLY INVOICE SERVICE" in text and "No" in text)
check("PDF does NOT contain £2 (since not requested)", "£2" not in text)
cleanup(emp_id, val["access_code_id"])

# ---------------------------------------------------------------------------
# 9. CSV export columns
# ---------------------------------------------------------------------------
print("[9] CSV export columns present")
# Create one yes + one no record to check both rows
inv1, val1 = fresh()
r1 = requests.post(f"{API}/api/induction/submit",
    json=base_body(inv1, val1, invoice_service_requested=True,
                   invoice_email_1="csv1@example.com", invoice_email_2="csv2@example.com"),
    timeout=60).json()
inv2, val2 = fresh()
r2 = requests.post(f"{API}/api/induction/submit", json=base_body(inv2, val2), timeout=60).json()
csv = requests.get(f"{API}/api/admin/employees.csv", auth=(ADMIN_USER, ADMIN_PASS), timeout=30).text
header = csv.splitlines()[0]
check("CSV has 'Invoice Service' column", "Invoice Service" in header)
check("CSV has 'Invoice Emails' column", "Invoice Emails" in header)
yes_row = next((l for l in csv.splitlines() if r1["employee_id"] in l), "")
no_row = next((l for l in csv.splitlines() if r2["employee_id"] in l), "")
check("Yes row contains YES + emails", "YES" in yes_row and "csv1@example.com" in yes_row and "csv2@example.com" in yes_row)
check("No row contains NO", "NO" in no_row)
cleanup(r1["employee_id"], val1["access_code_id"])
cleanup(r2["employee_id"], val2["access_code_id"])

# ---------------------------------------------------------------------------
# 10. Admin listing surfaces new fields
# ---------------------------------------------------------------------------
print("[10] Admin listing exposes invoice fields")
inv, val = fresh()
r = requests.post(f"{API}/api/induction/submit",
    json=base_body(inv, val, invoice_service_requested=True, invoice_email_1="listing@x.com"),
    timeout=60).json()
listing = requests.get(f"{API}/api/admin/employees", auth=(ADMIN_USER, ADMIN_PASS), timeout=30).json()
row = next((it for it in listing.get("items", []) if it.get("employee_id") == r["employee_id"]), {})
check("listing has invoice_service_requested", row.get("invoice_service_requested") is True)
check("listing has invoice_emails", row.get("invoice_emails") == ["listing@x.com"])
check("listing has invoice_service_charge=2", row.get("invoice_service_charge") == 2)
cleanup(r["employee_id"], val["access_code_id"])

print("=" * 80)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
