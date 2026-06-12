"""
Clean up test/demo records from production Firestore + Storage.

KEEP:  kPA2DyOOhpkzjhjSiCsg  (Valeria Lupanciuc, real induction)

DELETE:
  - 0EApcMofHgM1BpaqraJQ   (Test, 8 Jun 10:19)
  - YwT5Bp18VGXcN9VC1VXn   (Test, 8 Jun 12:00, approved)
  - ko6ESi5DeKeZlN1q594b   (Valeria, 8 Jun, rejected)

Touches collections: employee_summary, employees, medical_history,
havs_questionnaires, employee_documents, access_codes (by employee_id),
email_logs (by employee_id) + Storage folder under storage_folder_path.

The KEEP doc is never referenced for writes — every delete is guarded
against the keep_id to make accidental deletion impossible.
"""
from __future__ import annotations

import base64
import json
import os
import sys

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage as fb_storage
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv("/app/backend/.env")

KEEP_ID = "kPA2DyOOhpkzjhjSiCsg"
DELETE_IDS = [
    "0EApcMofHgM1BpaqraJQ",
    "YwT5Bp18VGXcN9VC1VXn",
    "ko6ESi5DeKeZlN1q594b",
]
ASSOC_DOC_COLLECTIONS = [
    "employee_summary",
    "employees",
    "medical_history",
    "havs_questionnaires",
    "employee_documents",
]
QUERY_COLLECTIONS = [
    ("access_codes", "employee_id"),
    ("email_logs", "employee_id"),
]

assert KEEP_ID not in DELETE_IDS, "Safety: KEEP_ID must not be in DELETE_IDS"

DRY_RUN = "--apply" not in sys.argv

b64 = os.environ["FIREBASE_SERVICE_ACCOUNT_B64"]
sa = json.loads(base64.b64decode(b64))
cred = credentials.Certificate(sa)
firebase_admin.initialize_app(cred, {
    "storageBucket": os.environ["FIREBASE_STORAGE_BUCKET"],
})
db = firestore.client()
bucket = fb_storage.bucket()

mode = "DRY-RUN (no changes)" if DRY_RUN else "APPLY (deleting)"
print(f"Mode: {mode}")
print(f"Project: {sa['project_id']}   Bucket: {bucket.name}")
print(f"KEEP:    {KEEP_ID}")
print(f"DELETE:  {DELETE_IDS}")
print("=" * 90)

# Hard safety check — abort if the keep record would be touched.
keep_snap = db.collection("employee_summary").document(KEEP_ID).get()
if not keep_snap.exists:
    print(f"ABORT: keep record {KEEP_ID} not found in employee_summary")
    sys.exit(1)
print(f"Keep record verified: {keep_snap.to_dict().get('full_name')!r} "
      f"({keep_snap.to_dict().get('email')}) status={keep_snap.to_dict().get('review_status')}")
print()

totals = {"firestore_docs": 0, "storage_blobs": 0, "storage_folders": 0}

for emp_id in DELETE_IDS:
    if emp_id == KEEP_ID:
        print(f"!! REFUSE to touch keep id {emp_id}")
        continue

    print(f"--- {emp_id} ---")

    summary_snap = db.collection("employee_summary").document(emp_id).get()
    summary = summary_snap.to_dict() if summary_snap.exists else {}
    storage_folder = summary.get("storage_folder_path") if summary else None
    print(f"   full_name       = {summary.get('full_name')!r}")
    print(f"   email           = {summary.get('email')!r}")
    print(f"   submitted_at    = {summary.get('submitted_at')!r}")
    print(f"   review_status   = {summary.get('review_status')!r}")
    print(f"   storage_folder  = {storage_folder!r}")

    # Direct doc-id collections
    for col in ASSOC_DOC_COLLECTIONS:
        ref = db.collection(col).document(emp_id)
        snap = ref.get()
        if snap.exists:
            print(f"   [doc]  {col}/{emp_id}")
            totals["firestore_docs"] += 1
            if not DRY_RUN:
                ref.delete()

    # Query-based collections (access_codes, email_logs)
    for col, field in QUERY_COLLECTIONS:
        q = db.collection(col).where(filter=FieldFilter(field, "==", emp_id))
        for d in q.stream():
            print(f"   [doc]  {col}/{d.id}   (matched {field}={emp_id})")
            totals["firestore_docs"] += 1
            if not DRY_RUN:
                d.reference.delete()

    # Storage folder
    if storage_folder:
        prefix = storage_folder.rstrip("/") + "/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        print(f"   [blob] {len(blobs)} object(s) under {prefix}")
        for blob in blobs:
            print(f"          {blob.name}")
            totals["storage_blobs"] += 1
            if not DRY_RUN:
                blob.delete()
        if blobs:
            totals["storage_folders"] += 1

    print()

print("=" * 90)
print(f"Summary: firestore_docs={totals['firestore_docs']}  "
      f"storage_blobs={totals['storage_blobs']}  "
      f"storage_folders={totals['storage_folders']}")
print()

# Final verification of keep record
print("Post-run check of KEEP record:")
keep_after = db.collection("employee_summary").document(KEEP_ID).get()
print(f"  employee_summary/{KEEP_ID} exists = {keep_after.exists}")
for col in ["employees", "medical_history", "havs_questionnaires", "employee_documents"]:
    s = db.collection(col).document(KEEP_ID).get()
    print(f"  {col}/{KEEP_ID} exists = {s.exists}")

if DRY_RUN:
    print()
    print("DRY-RUN complete. Re-run with `--apply` to actually delete.")
