"""End-to-end verification of the review-status fixes.

Creates a synthetic 'PNC Diag Contractor' record, exercises the full review
flow, and asserts:

  1. First approve  -> 200, review_status="approved", audit entry appended,
                       BOTH emails (contractor + manager) sent with distinct
                       Resend message IDs, redirected_from=null on both.
  2. Second approve -> idempotent=True, NO new emails.
  3. Stale approve with wrong if_previous_status -> 409.
  4. Reset to pending with correct if_previous_status -> 200, audit entry
                       appended, NO emails.
  5. Backend restart -> status still "approved" (well, still whatever we
                       left it in step 4) after re-reading Firestore.

Cleans up the test doc at the end. Reads admin creds from backend/.env.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from firebase_client import get_firestore

db = get_firestore()

BACKEND_URL = "http://127.0.0.1:8001"
ADMIN = (os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])


def _fail(msg: str) -> None:
    print(f"\n❌ FAIL: {msg}")
    sys.exit(1)


def _pass(msg: str) -> None:
    print(f"  ✅ {msg}")


def _emails_for(employee_id: str, purpose: str | None = None) -> list[dict]:
    q = db.collection("email_logs").where("employee_id", "==", employee_id)
    if purpose:
        q = q.where("purpose", "==", purpose)
    docs = list(q.stream())
    return [d.to_dict() for d in docs]


def _summary(employee_id: str) -> dict:
    snap = db.collection("employee_summary").document(employee_id).get()
    return snap.to_dict() or {}


def main() -> int:
    # ---------------------------------------------------------------
    # 0) Create synthetic test induction (bypasses the wizard so we
    #    don't spam file storage — writes directly to Firestore).
    # ---------------------------------------------------------------
    now = datetime.now(timezone.utc).isoformat()
    test_email = "diagbot+approve@pncunique.com"
    test_name = "PNC Diag Contractor"
    ref = db.collection("employee_summary").document()
    ref.set({
        "full_name": test_name,
        "email": test_email,
        "invited_email": test_email,
        "submitted_at": now,
        "summary_generated_at": now,
        "review_status": "pending_review",
        "induction_status": "Submitted",
        "medical_status": "OK",
        "pdf_url": "https://example.invalid/diagbot.pdf",
        "company_name": "PNC Diag Ltd",
        "diagnostic": True,   # marker so cleanup only touches this record
    })
    emp_id = ref.id
    # Mirror in employees so admin listing shows it.
    db.collection("employees").document(emp_id).set({
        "full_name": test_name,
        "email": test_email,
        "diagnostic": True,
    })
    print(f"\n🧪 Created test induction: {emp_id}")

    try:
        # -----------------------------------------------------------
        # 1) First approve — expect 200, audit entry, TWO email sends
        # -----------------------------------------------------------
        print("\n[1] First approve — expect success + two distinct emails")
        r = requests.patch(
            f"{BACKEND_URL}/api/admin/employees/{emp_id}/review",
            auth=ADMIN,
            json={
                "review_status": "approved",
                "manager_email": "admin@pncunique.com",
                "if_previous_status": "pending_review",
            },
            timeout=30,
        )
        if r.status_code != 200:
            _fail(f"expected 200, got {r.status_code}: {r.text}")
        body = r.json()
        if body.get("review_status") != "approved":
            _fail(f"review_status != approved: {body}")
        _pass(f"HTTP 200 · review_status=approved · email_status={body.get('email_status')} · manager_email_status={body.get('manager_email_status')}")
        appended = body.get("review_history_appended") or {}
        if appended.get("from") != "pending_review" or appended.get("to") != "approved":
            _fail(f"review_history_appended wrong: {appended}")
        _pass(f"audit entry appended: {appended['from']} -> {appended['to']} at {appended.get('at')}")

        # Confirm Firestore state
        time.sleep(0.5)
        s = _summary(emp_id)
        if s.get("review_status") != "approved":
            _fail(f"Firestore review_status != approved: {s.get('review_status')}")
        hist = s.get("review_history") or []
        if not any(h.get("to") == "approved" and h.get("from") == "pending_review" for h in hist):
            _fail(f"review_history array missing entry: {hist}")
        _pass(f"Firestore review_history now has {len(hist)} entry")

        # Confirm the two email log rows exist and are distinct
        contractor_logs = _emails_for(emp_id, purpose="review_approved")
        manager_logs = _emails_for(emp_id, purpose="manager_approval_notification")
        if len(contractor_logs) != 1:
            _fail(f"expected 1 contractor email log, got {len(contractor_logs)}: {contractor_logs}")
        if len(manager_logs) != 1:
            _fail(f"expected 1 manager email log, got {len(manager_logs)}: {manager_logs}")
        c, m = contractor_logs[0], manager_logs[0]
        if c.get("message_id") == m.get("message_id"):
            _fail("contractor and manager have IDENTICAL message ids")
        _pass(f"contractor msg_id={c.get('message_id')} → {c.get('to')} (status={c.get('status')})")
        _pass(f"manager    msg_id={m.get('message_id')} → {m.get('to')} (status={m.get('status')})")
        if c.get("redirected_from") is not None:
            _fail(f"contractor send was redirected: {c.get('redirected_from')}")
        if m.get("redirected_from") is not None:
            _fail(f"manager send was redirected: {m.get('redirected_from')}")
        _pass("no test-override redirect on either send")
        if c.get("to") == m.get("to"):
            _fail(f"both sends went to same address: {c.get('to')}")
        if c.get("to") != test_email:
            _fail(f"contractor email did not go to inductee address: to={c.get('to')} expected={test_email}")
        _pass(f"contractor received the approval, admin received the notification (2 distinct recipients)")

        # -----------------------------------------------------------
        # 2) Second approve — idempotent short-circuit
        # -----------------------------------------------------------
        print("\n[2] Second approve — expect idempotent no-op + NO new emails")
        r2 = requests.patch(
            f"{BACKEND_URL}/api/admin/employees/{emp_id}/review",
            auth=ADMIN,
            json={
                "review_status": "approved",
                "manager_email": "admin@pncunique.com",
                "if_previous_status": "approved",
            },
            timeout=30,
        )
        if r2.status_code != 200:
            _fail(f"expected 200, got {r2.status_code}: {r2.text}")
        b2 = r2.json()
        if not b2.get("idempotent"):
            _fail(f"expected idempotent=True: {b2}")
        _pass(f"idempotent=True, email_status={b2.get('email_status')}, manager_email_status={b2.get('manager_email_status')}")

        # Verify NO new email logs appeared
        time.sleep(0.5)
        c2 = _emails_for(emp_id, purpose="review_approved")
        m2 = _emails_for(emp_id, purpose="manager_approval_notification")
        if len(c2) != 1:
            _fail(f"duplicate contractor email created: {len(c2)}")
        if len(m2) != 1:
            _fail(f"duplicate manager email created: {len(m2)}")
        _pass("no duplicate email sends — idempotency confirmed")

        # -----------------------------------------------------------
        # 3) Stale write — client thinks state was pending, but it's approved
        # -----------------------------------------------------------
        print("\n[3] Stale write with wrong if_previous_status — expect 409")
        r3 = requests.patch(
            f"{BACKEND_URL}/api/admin/employees/{emp_id}/review",
            auth=ADMIN,
            json={
                "review_status": "approved",
                "if_previous_status": "pending_review",  # <- stale
            },
            timeout=30,
        )
        if r3.status_code != 409:
            _fail(f"expected 409, got {r3.status_code}: {r3.text}")
        _pass(f"409 returned as expected · body: {r3.text[:180]}")

        # -----------------------------------------------------------
        # 4) Reset to pending with correct if_previous_status
        # -----------------------------------------------------------
        print("\n[4] Reset to pending — expect audit entry + NO new emails")
        r4 = requests.patch(
            f"{BACKEND_URL}/api/admin/employees/{emp_id}/review",
            auth=ADMIN,
            json={
                "review_status": "pending_review",
                "if_previous_status": "approved",
            },
            timeout=30,
        )
        if r4.status_code != 200:
            _fail(f"expected 200, got {r4.status_code}: {r4.text}")
        b4 = r4.json()
        if b4.get("review_status") != "pending_review":
            _fail(f"expected review_status=pending_review, got: {b4}")
        _pass(f"HTTP 200 · review_status=pending_review · email_status={b4.get('email_status')} · manager_email_status={b4.get('manager_email_status')}")

        # No new email logs
        time.sleep(0.5)
        c3 = _emails_for(emp_id, purpose="review_approved")
        m3 = _emails_for(emp_id, purpose="manager_approval_notification")
        if len(c3) != 1 or len(m3) != 1:
            _fail(f"unexpected email logs after pending reset: contractor={len(c3)} manager={len(m3)}")
        _pass("no new emails on pending reset")

        # Audit trail growth
        s4 = _summary(emp_id)
        hist4 = s4.get("review_history") or []
        if len(hist4) != 2:
            _fail(f"expected 2 audit entries, have {len(hist4)}: {hist4}")
        _pass(f"audit trail now: {[h.get('from')+' -> '+h.get('to') for h in hist4]}")

        # -----------------------------------------------------------
        # 5) Backend restart survives the state
        # -----------------------------------------------------------
        print("\n[5] Backend restart — state should survive")
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
        time.sleep(4)
        # Wait for /api/health
        for _ in range(20):
            try:
                if requests.get(f"{BACKEND_URL}/api/health", timeout=2).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        s5 = _summary(emp_id)
        if s5.get("review_status") != "pending_review":
            _fail(f"after restart, review_status changed: {s5.get('review_status')}")
        _pass(f"post-restart review_status still 'pending_review'")

        # Re-read after restart — do NOT re-approve. State check only, to
        # keep the test from sending yet more real Resend messages.
        for i in range(5):
            time.sleep(0.2)
            if _summary(emp_id).get("review_status") != "pending_review":
                _fail(f"read #{i+1} showed non-pending state after restart")
        _pass("5× refresh post-restart: state remains 'pending_review' (durable)")

        print("\n🎉 ALL 5 SUB-TESTS PASSED")
        return 0
    finally:
        # Cleanup — remove the diag record and any email logs we created
        db.collection("employee_summary").document(emp_id).delete()
        db.collection("employees").document(emp_id).delete()
        for L in db.collection("email_logs").where("employee_id", "==", emp_id).stream():
            L.reference.delete()
        print(f"\n🧹 Cleaned up test record {emp_id} and its email logs")


if __name__ == "__main__":
    raise SystemExit(main())
