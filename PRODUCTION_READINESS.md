# PNC Induction Portal — Production Readiness Review

_Date: 2026-02-09_  _Reviewer: E1_

This audit covers every subsystem that touches real PNC data. Findings are
tagged **OK** (no action), **WATCH** (recommended but not blocking), or
**FIX** (do before declaring v1.0 GA).

---

## 1. Firebase security rules
- **OK** — Firestore rules in `SETUP_FIREBASE.md` lock all five collections at the client. `employee_summary` is explicitly `allow read, write: if false` so only the Admin SDK can read/write.
- **OK** — Storage rules allow `write` only for files ≤10 MB and JPG/PNG/PDF; `read` is open so the backend can sign PDFs.
- **WATCH** — Storage `read: true` means anyone with the long token-protected URL can fetch the file. The Firebase download token already provides per-file capability so this is acceptable; revisit if you ever move to App Check.

## 2. Firestore collections
- **OK** — Five spec collections (`employees`, `medical_history`, `havs_questionnaires`, `employee_documents`, `access_codes`) all linked by `employee_id`.
- **OK** — Two backend-managed collections: `employee_summary` (master HR record) and `email_logs` (audit).
- **OK** — `employee_summary` doc ID equals the `employee_id` → idempotent updates, easy lookup.

## 3. Storage permissions & folder layout
- **OK** — New submissions land in `employees/{slug(full_name)}-{employee_id}/…` (browsable in the Firebase Console).
- **OK** — Legacy records preserved at `employees/{employee_id}/…`; backend uses each file's own stored `path`, never reconstructs.
- **OK** — PDF location follows the same folder pattern.

## 4. Admin authentication
- **OK** — HTTP Basic Auth via FastAPI `HTTPBasic(realm="PNC Admin")`; credentials checked with `secrets.compare_digest`.
- **OK** — Credentials live only in `backend/.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
- **WATCH** — Single shared admin account. For v1.1 consider Firebase-Auth-backed per-user logins so the audit log can attribute approvals/rejections to a specific HR person.

## 5. API security
- **OK** — Every admin route requires Basic Auth via `dependencies=[Depends(require_admin)]`.
- **OK** — Public endpoints (`/api/health`, `/api/induction/finalize`) carry no PII inputs aside from a server-side-generated employee_id.
- **WATCH** — `/api/induction/finalize` is currently open. Real-world attack vector is low (you must know an employee_id), but you can harden by requiring an HMAC the gate hands the wizard. v1.1 nice-to-have.
- **OK** — CORS reads from `CORS_ORIGINS` env var (currently `*`). For prod hardening, set to `https://induct-pro.emergent.host` once you're sure no other tool calls the API.

## 6. Resend configuration
- **OK** — API key only in `backend/.env`; never serialised to the frontend; never logged (`email_service.py` strips errors to `type(exc).__name__`).
- **OK** — Test-mode override (`RESEND_TEST_OVERRIDE_EMAIL`) routes every email to the Resend account owner until the PNC domain is verified.
- **FIX before GA** — Verify a PNC-owned domain in Resend (`induction@pnc.co.uk`), update `SENDER_EMAIL`, **remove** `RESEND_TEST_OVERRIDE_EMAIL`. Until this is done, real inductees do **not** receive the invitation/approval/rejection emails.

## 7. Environment variables
Keys observed in `backend/.env`:
`MONGO_URL, DB_NAME, CORS_ORIGINS, FIREBASE_SERVICE_ACCOUNT_B64,
FIREBASE_STORAGE_BUCKET, ADMIN_USERNAME, ADMIN_PASSWORD, RESEND_API_KEY,
SENDER_EMAIL, PUBLIC_PORTAL_URL, RESEND_TEST_OVERRIDE_EMAIL`

`frontend/.env`: `REACT_APP_BACKEND_URL` + `REACT_APP_FIREBASE_*`.

- **OK** — No secrets in source code; no `.env` files in git.
- **WATCH** — `MONGO_URL` / `DB_NAME` are unused legacy keys (the app uses Firestore). Safe to leave; can be cleaned up.

## 8. Error handling
- **OK** — User-facing wizard catches submission errors and shows a friendly message without wiping local progress.
- **OK** — Admin endpoints return clean 401 / 404 / 422 with helpful detail.
- **OK** — Email send failures are logged in `email_logs` and surface as `email_status: "failed"` in API responses + UI toasts.
- **WATCH** — Frontend `/api/induction/finalize` call after submission is best-effort. If it ever fails silently the inductee still sees Success. Acceptable because finalize is idempotent — HR can re-trigger from the admin portal (Phase 4 idea).

## 9. PDF generation
- **OK** — ReportLab renders A4 PDF with brand band, all 6 sections, embedded drawn signature, per-page footer.
- **OK** — Re-runs overwrite the same Storage path; URL stable via Firebase download token.
- **WATCH** — `_make_public_url` writes a download token on every finalize → 1 extra Storage round-trip. Minor cost.

## 10. Invite workflow
- **OK** — `POST /api/admin/invites` mints a unique `PNC-XXXX-XXXX` code (32-char alphabet, no ambiguous chars), writes to `access_codes`, optionally sends email, returns paste-ready invitation text.
- **OK** — Frontend modal supports Send Email vs Just Create Code; copy buttons for code and full invitation.

## 11. Approval workflow
- **OK** — `PATCH /api/admin/employees/{id}/review` with `review_status=approved` sets `review_status`, `reviewed_at`, sends approval email subject `PNC Induction Approved`, logs to `email_logs`.
- **OK** — Confirmation modal in the dashboard with subject-line preview.

## 12. Rejection workflow
- **OK** — Required note enforced both client- and server-side (Pydantic `Field`/`Form`).
- **OK** — Mints a new access code, writes `access_codes` doc with `invite_status: "resent_after_rejection"`, fills the inductee's email/name/`related_rejected_employee_id`/`rejection_reason`.
- **OK** — Updates `employee_summary` with `resubmission_code`, `resubmission_requested: true`, `resubmission_access_code_id`.
- **OK** — Email contains the new code, portal link and explicit resubmission instructions.

## 13. Access code lifecycle
- **OK** — Created (created / sent / resent_after_rejection) → Used (gate sets `used: true`, `used_at`, `employee_id`) → Reviewed (approved or rejected; rejection mints a fresh code).
- **OK** — One-time semantics enforced by the gate (`if data.used: error`).

## 14. Email logging
- **OK** — Every email (sent/failed/skipped/redirected) creates an `email_logs` doc with subject, recipient, redirect target, purpose, employee_id and `message_id`.
- **WATCH** — `email_logs` has no client read access (correct) but no admin UI yet. The audit trail exists in Firestore Console only.

## 15. CSV export
- **OK** — UTF-8 BOM + CRLF; headers in PNC's exact spreadsheet order; values formatted human-friendly (Yes/No / "Pending Review" instead of `pending_review`).
- **OK** — Filters: `q`, `email`, `ni`, `company`, `review_status`, `date_from`, `date_to`.
- **OK** — Browser/Excel/Sheets auth flow tested.

## 16. Admin portal permissions
- **OK** — `/admin/*` routes are public to the React app but every API call requires Basic Auth.
- **WATCH** — A determined attacker who guesses the admin password could PATCH any record. Pair with a strong password rotation policy (see checklist below).

---

## Unfinished / nice-to-have
- Re-send invite button on stale invitations.
- "Resubmission codes" filter on the Invitations page.
- Email-log tooltip per employee row in the admin table.
- Per-user admin accounts (currently one shared account).
- HMAC-guarded `/api/induction/finalize`.

## Technical debt
- Legacy `MONGO_URL` / `DB_NAME` env keys unused.
- Three debug scripts in `backend/` were already deleted; check no test data lingers in Firestore.

## Production risks
1. **Resend test mode** — until the PNC domain is verified, real inductees do not receive email.
2. **Single shared admin password** — rotation discipline matters.
3. **CORS `*`** — fine for now; lock down to the prod hostname for v1.1.

---

# Production Readiness Checklist

Tick these before declaring v1.0 GA.

- [ ] Firestore Security Rules published exactly as in `SETUP_FIREBASE.md`.
- [ ] Storage Rules published exactly as in `SETUP_FIREBASE.md`.
- [ ] `ADMIN_PASSWORD` rotated to a fresh value before handover (and shared with PNC HR over a secure channel — not email).
- [ ] PNC domain verified in Resend; `SENDER_EMAIL` updated; `RESEND_TEST_OVERRIDE_EMAIL` removed.
- [ ] CORS locked to `https://induct-pro.emergent.host` after every external integration is confirmed.
- [ ] One real induction tested end-to-end on production: invite → submit → PDF → approve → email received.
- [ ] One rejection tested end-to-end on production: reject with note → email contains new code → inductee resubmits.
- [ ] `employee_summary` reviewed in Firebase Console for any stale test rows; delete or label.
- [ ] `email_logs` reviewed for failed sends.
- [ ] Admin User Guide (`ADMIN_USER_GUIDE.pdf`) distributed to PNC HR.
- [ ] Backup plan documented: Firebase Firestore export schedule + Storage bucket retention.
- [ ] Incident runbook agreed: who to call if Resend, Firebase or the Emergent host has an outage.
