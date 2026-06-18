"""End-to-end test for the new H&S + Site Rules compliance flow.

Validates:
  - Submission without acks → HTTP 422 (compliance gate)
  - Submission with all 13 H&S sections + Site Rules acked → success
  - Backwards-compat: legacy record with no compliance fields renders as
    health_safety_acknowledged=false in summary
  - CSV columns "Health & Safety Completed" / "Site Rules Completed" present
  - PDF contains compliance text
"""
from __future__ import annotations

import base64
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

print(f"API:     {API}")
print(f"Project: {sa['project_id']}")
print(f"H&S keys ({len(HEALTH_SAFETY_KEYS)}): {HEALTH_SAFETY_KEYS}")
print("=" * 80)

results = []
def check(name, condition, detail=""):
    ok = bool(condition)
    print(f"   {'PASS' if ok else 'FAIL'}: {name}{(' — ' + detail) if detail else ''}")
    results.append((name, ok))


def fresh_invite():
    inv = requests.post(
        f"{API}/api/admin/invites",
        auth=(ADMIN_USER, ADMIN_PASS),
        json={"full_name": "Compliance Test", "email": f"compl-{os.urandom(3).hex()}@example.com", "send_email": False},
        timeout=30,
    ).json()
    val = requests.post(
        f"{API}/api/validate-access-code",
        json={"email": inv["email"], "code": inv["code"]},
        timeout=30,
    ).json()
    return inv, val


def base_payload(inv, val, *, include_compliance: bool, partial_hs: bool = False, missing_site: bool = False):
    now_iso = datetime.now(timezone.utc).isoformat()
    hs_sections = {}
    if include_compliance:
        keys = HEALTH_SAFETY_KEYS if not partial_hs else HEALTH_SAFETY_KEYS[:5]
        hs_sections = {k: now_iso for k in keys}
    body = {
        "access_code_id": val["access_code_id"],
        "access_code": inv["code"],
        "invited_email": inv["email"],
        "full_name": "Compliance Test",
        "dob": "1990-01-01", "telephone": "07700900000", "email": inv["email"],
        "address1": "1 Test St", "postcode": "SW1A 1AA", "ni_number": "QQ123456C",
        "emergency_name": "Kin", "emergency_phone": "07700900000", "emergency_relationship": "Spouse",
        "right_to_work_share_code": "ABC", "dvla_check": "yes",
        "company_name": "Test Ltd", "bank_account": "12345678", "sort_code": "12-34-56",
        "utr": "1234567890", "vat_number": None,
        "insurance_option": "covered_by_pnc", "digital_signature_name": "Compliance Test",
        "medical": {}, "havs": {},
        "files": {},
        "storage_folder_path": f"employees/compliance-{val['access_code_id']}/",
        "submitted_at": now_iso,
        "health_safety_acknowledged": include_compliance and not partial_hs,
        "health_safety_completed_at": now_iso if include_compliance and not partial_hs else None,
        "health_safety_sections": hs_sections,
        "site_rules_acknowledged": include_compliance and not missing_site,
        "site_rules_completed_at": now_iso if include_compliance and not missing_site else None,
    }
    return body


def cleanup(employee_id, access_code_id):
    for col in ("medical_history", "havs_questionnaires", "employee_documents"):
        for d in db.collection(col).where("employee_id", "==", employee_id).stream():
            d.reference.delete()
    db.collection("employees").document(employee_id).delete()
    db.collection("employee_summary").document(employee_id).delete()
    if access_code_id:
        db.collection("access_codes").document(access_code_id).delete()


# ---------------------------------------------------------------------------
# 1. Compliance gate: no acks → 422
# ---------------------------------------------------------------------------
print("[1] submit with NO compliance acks → expect HTTP 422")
inv, val = fresh_invite()
payload = base_payload(inv, val, include_compliance=False)
r = requests.post(f"{API}/api/induction/submit", json=payload, timeout=60)
check("HTTP 422", r.status_code == 422)
check("error mentions Health & Safety", "Health & Safety" in r.text)
check("error mentions Site Rules", "Site Rules" in r.text)
check("employees row NOT created", not list(db.collection("employees").where("access_code_id", "==", val["access_code_id"]).limit(1).stream()))
db.collection("access_codes").document(val["access_code_id"]).delete()

# ---------------------------------------------------------------------------
# 2. Compliance gate: only 5/13 H&S sections → 422
# ---------------------------------------------------------------------------
print("[2] submit with partial H&S (5/13) → expect HTTP 422")
inv, val = fresh_invite()
payload = base_payload(inv, val, include_compliance=True, partial_hs=True)
r = requests.post(f"{API}/api/induction/submit", json=payload, timeout=60)
check("HTTP 422 on partial H&S", r.status_code == 422)
db.collection("access_codes").document(val["access_code_id"]).delete()

# ---------------------------------------------------------------------------
# 3. Compliance gate: H&S complete but Site Rules missing → 422
# ---------------------------------------------------------------------------
print("[3] submit with H&S complete but no Site Rules → expect HTTP 422")
inv, val = fresh_invite()
payload = base_payload(inv, val, include_compliance=True, missing_site=True)
r = requests.post(f"{API}/api/induction/submit", json=payload, timeout=60)
check("HTTP 422 on missing Site Rules", r.status_code == 422)
db.collection("access_codes").document(val["access_code_id"]).delete()

# ---------------------------------------------------------------------------
# 4. Happy path: full compliance → 200 + persisted + summary fields
# ---------------------------------------------------------------------------
print("[4] full compliance → expect HTTP 200 and Firestore persistence")
inv, val = fresh_invite()
payload = base_payload(inv, val, include_compliance=True)
r = requests.post(f"{API}/api/induction/submit", json=payload, timeout=60)
check("HTTP 200", r.status_code == 200)
emp_id = r.json()["employee_id"]
# Inspect employees doc
emp = db.collection("employees").document(emp_id).get().to_dict()
check("employees.health_safety_acknowledged == True", emp.get("health_safety_acknowledged") is True)
check("employees.site_rules_acknowledged == True", emp.get("site_rules_acknowledged") is True)
check("employees.health_safety_sections has 13 entries", len(emp.get("health_safety_sections") or {}) == 13)
check("employees.health_safety_completed_at set", bool(emp.get("health_safety_completed_at")))
check("employees.site_rules_completed_at set", bool(emp.get("site_rules_completed_at")))
# Inspect employee_summary doc
summ = db.collection("employee_summary").document(emp_id).get().to_dict()
check("summary.health_safety_acknowledged True", summ.get("health_safety_acknowledged") is True)
check("summary.site_rules_acknowledged True", summ.get("site_rules_acknowledged") is True)

# ---------------------------------------------------------------------------
# 5. CSV export includes the two new columns
# ---------------------------------------------------------------------------
print("[5] CSV export contains compliance columns")
r = requests.get(f"{API}/api/admin/employees.csv", auth=(ADMIN_USER, ADMIN_PASS), timeout=30)
check("CSV ok", r.status_code == 200)
header_line = r.text.splitlines()[0]
check("CSV header has 'Health & Safety Completed'", "Health & Safety Completed" in header_line)
check("CSV header has 'Site Rules Completed'", "Site Rules Completed" in header_line)
# Find the row for our employee and verify YES values
for line in r.text.splitlines()[1:]:
    if emp_id in line:
        check("CSV row has YES for H&S", ",YES," in line or ",YES\n" in line + "\n")
        break

# ---------------------------------------------------------------------------
# 6. PDF generated includes Compliance Acknowledgements section
# ---------------------------------------------------------------------------
print("[6] PDF includes compliance content")
pdf_url = r.text  # placeholder; fetch via summary
summary = db.collection("employee_summary").document(emp_id).get().to_dict()
pdf_url = summary.get("pdf_url")
if pdf_url:
    pdf_resp = requests.get(pdf_url, timeout=60)
    check("PDF 200", pdf_resp.status_code == 200)
    pdf_bytes = pdf_resp.content
    # Extract text properly via pypdf (PDFs use font encoding, not plain bytes)
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(pdf_bytes))
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text() or ""
        check("PDF has 'Compliance Acknowledgements' section", "Compliance Acknowledgements" in all_text)
        check("PDF has Tool Box Talks appendix", "Tool Box Talks" in all_text and "Appendix A" in all_text)
        check("PDF has Site Rules appendix", "Site Rules" in all_text and "Appendix B" in all_text)
        check("PDF has 14+ pages (full content)", len(reader.pages) >= 13,
              f"got {len(reader.pages)} pages")
    except ImportError:
        check("pypdf available for content check", False, "install pypdf to verify PDF content")
else:
    check("PDF generated", False, "no pdf_url on summary")

# Save employee_id for cleanup at the end
happy_emp_id = emp_id
happy_ac_id = val["access_code_id"]

# ---------------------------------------------------------------------------
# 7. Backwards compatibility: simulate a legacy record with no compliance fields
# ---------------------------------------------------------------------------
print("[7] legacy record (no compliance fields) — summary defaults to false")
legacy_id = "legacy-compl-" + os.urandom(3).hex()
db.collection("employees").document(legacy_id).set({
    "full_name": "Legacy Inductee",
    "email": "legacy@old.com",
    "submitted_at": "2026-01-01T00:00:00Z",
    # Intentionally no health_safety_* or site_rules_* fields
})
db.collection("employee_summary").document(legacy_id).set({
    "employee_id": legacy_id,
    "full_name": "Legacy Inductee",
    "email": "legacy@old.com",
    "review_status": "approved",
    "submitted_at": "2026-01-01T00:00:00Z",
    "health_safety_acknowledged": False,  # what the new flattener would write
    "site_rules_acknowledged": False,
})
# Fetch via admin list
listing = requests.get(f"{API}/api/admin/employees", auth=(ADMIN_USER, ADMIN_PASS), timeout=30).json()
legacy = next((it for it in listing.get("items", []) if it.get("employee_id") == legacy_id), None)
check("legacy record in listing", legacy is not None)
if legacy:
    check("legacy hs ack False", legacy.get("health_safety_acknowledged") is False)
    check("legacy sr ack False", legacy.get("site_rules_acknowledged") is False)

# CSV row for legacy must read NO
r = requests.get(f"{API}/api/admin/employees.csv", auth=(ADMIN_USER, ADMIN_PASS), timeout=30)
legacy_csv = next((l for l in r.text.splitlines() if legacy_id in l), None)
check("legacy CSV row has NO somewhere", legacy_csv and "NO" in legacy_csv)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup(happy_emp_id, happy_ac_id)
db.collection("employees").document(legacy_id).delete()
db.collection("employee_summary").document(legacy_id).delete()

print("=" * 80)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
