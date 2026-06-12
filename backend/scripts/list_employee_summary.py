"""
Preview-only script. Lists every record in `employee_summary` so we can
confirm which IDs to delete BEFORE writing any delete calls.

Run from /app/backend with the existing .env service account.
"""
from __future__ import annotations

import base64
import json
import os
import sys

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv("/app/backend/.env")

b64 = os.environ["FIREBASE_SERVICE_ACCOUNT_B64"]
sa_json = json.loads(base64.b64decode(b64))
cred = credentials.Certificate(sa_json)
firebase_admin.initialize_app(cred)
db = firestore.client()

print(f"Project: {sa_json['project_id']}")
print("=" * 100)
print(f"{'#':<3} {'doc_id':<40} {'full_name':<30} {'email':<30} {'submitted_at':<25} {'review_status':<15}")
print("-" * 100)

records = []
for doc in db.collection("employee_summary").stream():
    rec = doc.to_dict() or {}
    rec["_doc_id"] = doc.id
    records.append(rec)

records.sort(key=lambda r: r.get("submitted_at") or "")

for i, r in enumerate(records, 1):
    print(
        f"{i:<3} "
        f"{(r.get('_doc_id') or '')[:38]:<40} "
        f"{(r.get('full_name') or '')[:28]:<30} "
        f"{(r.get('email') or '')[:28]:<30} "
        f"{(r.get('submitted_at') or '')[:23]:<25} "
        f"{(r.get('review_status') or '')[:13]:<15}"
    )

print("-" * 100)
print(f"Total employee_summary records: {len(records)}")

print()
print("=== Related collection counts (per employee_id) ===")
for r in records:
    emp_id = r.get("employee_id") or r.get("_doc_id")
    counts = {}
    for col in ("employees", "medical_history", "havs_questionnaires", "employee_documents"):
        snap = db.collection(col).document(emp_id).get()
        counts[col] = "yes" if snap.exists else "-"
    access_codes = sum(1 for _ in db.collection("access_codes").where("employee_id", "==", emp_id).stream())
    counts["access_codes"] = access_codes
    print(f"  {r.get('full_name')!r:<30} id={emp_id}  {counts}")
