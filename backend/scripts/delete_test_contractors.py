"""One-shot cleanup — delete the four synthetic 'Test Contractor' records
created by the backend regression suite on 2026-07-14.

Usage:
    python backend/scripts/delete_test_contractors.py           # dry-run (default)
    python backend/scripts/delete_test_contractors.py --apply   # actually delete

The script is intentionally hard-coded to the four IDs shown to the admin
before deletion — it will refuse to touch any other record.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make backend/ importable so we reuse the existing Firestore client setup.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from firebase_client import get_firestore  # noqa: E402

db = get_firestore()


# --- Locked to the specific IDs identified for the operator ------------------
TARGET_IDS: tuple[str, ...] = (
    "AO5JjUFex1TXFkz7Ex2g",
    "Wz1f50nm3UttGTUNIwxM",
    "KDdCyr1pjPM6iNKyTv4h",
    "b32uCcbs2JhxVp1gJCZ3",
)

# Guard rail: refuse to delete anything whose name/email does not match the
# expected test values. This stops the script from wiping a real record even
# if the ID list were edited by mistake.
EXPECTED_NAME = "Test Contractor"
EXPECTED_EMAIL = "test.contractor@example.com"


def _linked_docs(collection: str, employee_id: str) -> list:
    return list(
        db.collection(collection)
        .where("employee_id", "==", employee_id)
        .stream()
    )


def _delete_docs(docs, dry_run: bool) -> int:
    count = 0
    for d in docs:
        if dry_run:
            print(f"    [dry-run] would delete {d.reference.path}")
        else:
            d.reference.delete()
            print(f"    deleted {d.reference.path}")
        count += 1
    return count


def process(employee_id: str, dry_run: bool) -> bool:
    print(f"\n=== {employee_id} ===")
    # 1) Load employee_summary (the admin dashboard row) to double-check
    #    identity before touching anything.
    summary = db.collection("employee_summary").document(employee_id).get()
    if not summary.exists:
        print("    employee_summary does not exist — skipping")
        return False
    data = summary.to_dict() or {}
    name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    print(f"    full_name = {name!r}")
    print(f"    email     = {email!r}")
    if name != EXPECTED_NAME or email != EXPECTED_EMAIL:
        print(
            f"    !! SAFETY GUARD: expected name={EXPECTED_NAME!r} "
            f"and email={EXPECTED_EMAIL!r} — SKIPPING"
        )
        return False

    total = 0
    # 2) employee_summary (dashboard row)
    if dry_run:
        print(f"    [dry-run] would delete employee_summary/{employee_id}")
    else:
        db.collection("employee_summary").document(employee_id).delete()
        print(f"    deleted employee_summary/{employee_id}")
    total += 1

    # 3) employees (raw doc)
    if db.collection("employees").document(employee_id).get().exists:
        if dry_run:
            print(f"    [dry-run] would delete employees/{employee_id}")
        else:
            db.collection("employees").document(employee_id).delete()
            print(f"    deleted employees/{employee_id}")
        total += 1

    # 4) Linked sub-records queried by employee_id
    for coll in ("medical_history", "havs_questionnaires", "employee_documents"):
        docs = _linked_docs(coll, employee_id)
        if not docs:
            print(f"    no {coll} rows for {employee_id}")
            continue
        total += _delete_docs(docs, dry_run)

    # 5) Any access_codes that were minted for this employee (rejection flow)
    codes = _linked_docs("access_codes", employee_id)
    if codes:
        total += _delete_docs(codes, dry_run)

    print(f"    -> {total} document(s) {'to delete' if dry_run else 'deleted'}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually delete")
    args = parser.parse_args()
    dry_run = not args.apply

    print("PNC test-contractor cleanup")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Target IDs ({len(TARGET_IDS)}): {', '.join(TARGET_IDS)}")

    hits = sum(1 for eid in TARGET_IDS if process(eid, dry_run))
    print(f"\nSummary: {hits}/{len(TARGET_IDS)} record(s) processed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
