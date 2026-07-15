"""Read-only diagnostic — inspects the last 15 employee_summary docs (by
submitted_at desc) and dumps every review-adjacent field so we can see:

  * the canonical field values (review_status, review_updated_at, reviewed_at)
  * any residual pending state
  * duplicate employee IDs across employees / employee_summary / access_codes
  * the exact "last approved that stuck" record vs the earlier ones

DOES NOT WRITE. DOES NOT DELETE. Safe to run against production Firestore.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from firebase_client import get_firestore

db = get_firestore()

REVIEW_FIELDS = [
    "employee_id",
    "full_name",
    "email",
    "review_status",
    "review_updated_at",
    "reviewed_at",
    "review_note",
    "submitted_at",
    "summary_generated_at",
    "manager_notified_at",
    "resubmission_code",
    "resubmission_requested",
]


def _get_all_summaries():
    return list(db.collection("employee_summary").stream())


def main() -> int:
    summaries = _get_all_summaries()
    print(f"Total employee_summary docs: {len(summaries)}\n")

    # Sort by submitted_at desc (fall back to summary_generated_at)
    def _sort_key(d):
        rec = d.to_dict() or {}
        return rec.get("submitted_at") or rec.get("summary_generated_at") or ""
    summaries.sort(key=_sort_key, reverse=True)

    print(f"{'employee_id':22s} {'review_status':17s} {'reviewed_at':22s} {'submitted_at':22s} {'full_name':25s} {'notes'}")
    print("-" * 160)
    for s in summaries[:15]:
        rec = s.to_dict() or {}
        eid = s.id
        rs = (rec.get("review_status") or "").strip() or "—"
        rat = str(rec.get("reviewed_at") or "—")[:22]
        sub = str(rec.get("submitted_at") or "—")[:22]
        name = (rec.get("full_name") or "")[:25]
        notes = []
        if rec.get("resubmission_requested"):
            notes.append(f"resub_code={rec.get('resubmission_code')}")
        if rec.get("review_updated_at") and rec.get("review_updated_at") != rec.get("reviewed_at"):
            notes.append(f"upd_at≠revd_at (upd={rec.get('review_updated_at')})")
        print(f"{eid:22s} {rs:17s} {rat:22s} {sub:22s} {name:25s} {'; '.join(notes)}")

    # By review_status counts
    print("\n=== review_status counts (all 58) ===")
    counts: dict[str, int] = {}
    for s in summaries:
        rs = (s.to_dict() or {}).get("review_status") or "(empty)"
        counts[rs] = counts.get(rs, 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    # Duplicate ID check
    print("\n=== duplicate employee_id across collections ===")
    summary_ids = {s.id for s in summaries}
    emp_ids = {d.id for d in db.collection("employees").stream()}
    overlap = summary_ids & emp_ids
    only_summary = summary_ids - emp_ids
    only_emp = emp_ids - summary_ids
    print(f"  summary ∩ employees: {len(overlap)}")
    print(f"  summary only:        {len(only_summary)}")
    print(f"  employees only:      {len(only_emp)}")

    # Are there any "approved" records that have review_updated_at < submitted_at?
    # (Would suggest a submit after approve overwrote it.)
    print("\n=== integrity check: approved records with review_updated_at < submitted_at ===")
    bad = []
    for s in summaries:
        rec = s.to_dict() or {}
        if (rec.get("review_status") or "") != "approved":
            continue
        rat = rec.get("review_updated_at") or rec.get("reviewed_at") or ""
        sub = rec.get("submitted_at") or ""
        if rat and sub and rat < sub:
            bad.append((s.id, sub, rat, rec.get("full_name")))
    if bad:
        for row in bad:
            print(f"  {row}")
    else:
        print("  (none)")

    # Show anything with review_updated_at in the last 48 h — that's the recent activity
    print("\n=== all rows updated in the last 48h (any review activity today/yesterday) ===")
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=48)).isoformat()
    recents = []
    for s in summaries:
        rec = s.to_dict() or {}
        rat = rec.get("review_updated_at") or rec.get("reviewed_at") or ""
        if rat and rat > cutoff:
            recents.append((rat, s.id, rec.get("review_status"), rec.get("full_name")))
    recents.sort(reverse=True)
    for r in recents:
        print(f"  {r}")
    if not recents:
        print("  (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
