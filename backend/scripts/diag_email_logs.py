"""Read-only diagnostic — inspects the last 30 email_logs docs to see:
  * status distribution (sent / failed / skipped)
  * failure reasons from Resend
  * whether contractor sends are being rejected
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from firebase_client import get_firestore
db = get_firestore()


def main() -> int:
    logs = list(db.collection("email_logs").stream())
    print(f"Total email_logs docs: {len(logs)}\n")

    def _key(d):
        r = d.to_dict() or {}
        return r.get("sent_at") or r.get("created_at") or ""
    logs.sort(key=_key, reverse=True)

    print("=== Last 30 email log entries ===")
    print(f"{'sent_at':22s} {'purpose':32s} {'status':14s} {'to':32s} {'from':38s} note")
    print("-" * 200)
    for d in logs[:30]:
        r = d.to_dict() or {}
        sat = str(r.get("sent_at") or r.get("created_at") or "")[:22]
        purpose = str(r.get("purpose") or "")[:32]
        status = str(r.get("status") or "")[:14]
        to = str(r.get("to") or "")[:32]
        frm = str(r.get("from") or "")[:38]
        # Look for any error / reason / redirected_from indicator
        parts = []
        if r.get("reason"): parts.append(f"reason={r['reason']}")
        if r.get("error"):  parts.append(f"error={r['error']}")
        if r.get("redirected_from"): parts.append(f"orig_to={r['redirected_from']}")
        if r.get("message_id"): parts.append(f"msg={r['message_id']}")
        note = "; ".join(parts)[:120]
        print(f"{sat:22s} {purpose:32s} {status:14s} {to:32s} {frm:38s} {note}")

    print("\n=== Status distribution across all logs ===")
    counts: dict[str, int] = {}
    for d in logs:
        s = (d.to_dict() or {}).get("status") or "(none)"
        counts[s] = counts.get(s, 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    print("\n=== Purpose distribution across all logs ===")
    counts2: dict[str, int] = {}
    for d in logs:
        p = (d.to_dict() or {}).get("purpose") or "(none)"
        counts2[p] = counts2.get(p, 0) + 1
    for k, v in sorted(counts2.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    # Look for any log with review_ prefix and its status
    print("\n=== All 'review_approved' logs (approval to contractor) — last 20 ===")
    approvals = [d for d in logs if (d.to_dict() or {}).get("purpose") == "review_approved"]
    for d in approvals[:20]:
        print(f"  {json.dumps(d.to_dict(), default=str, indent=2)[:500]}")
        print("  ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
