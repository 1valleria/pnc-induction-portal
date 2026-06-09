# PNC Induction Portal — PRD

## Original problem statement
Production-ready, mobile-first digital induction portal that replaces the existing Google Form → Google Sheet → manual CSV → manual PDF process. Users complete a 3-step form (Personal/Business/Insurance + Medical/HAVS + Signature) and submissions are written directly to the existing Firestore collections in the customer's Firebase project. No admin dashboard — admins use Firebase Console directly.

## User personas
- **Subcontractor / new employee**: completes the induction once on mobile, often on a phone, may pause and resume.
- **PNC HR admin**: works inside Firebase Console — distributes one-time access codes, reads submitted records, downloads PDFs.

## Core requirements (static)
- 3-step wizard with sticky progress bar, mobile-first layout
- Access code + email gate (validates against `access_codes` Firestore collection)
- Sections: Personal Info, Business, Insurance (conditional upload), Medical History (15 yes/no + 2 textareas), HAVS Questionnaire (8 yes/no), Digital Signature (typed name + drawn canvas)
- File uploads (jpg/png/pdf, 10 MB max) → Firebase Storage at `employees/{employeeId}/{slot}/`
- Auto-save progress to localStorage with visible indicator
- Writes link via `employee_id` to the existing collections: `employees`, `medical_history`, `havs_questionnaires`, `employee_documents`
- One-time access code marked `used: true` after successful submission
- Server-side PDF generation (deferred to next phase)

## What's been implemented (2026-02-08)
- Firebase Web SDK init from env (`/app/frontend/src/lib/firebase.js`)
- Access code gate at `/` validates code + email against `access_codes` (`AccessGate.jsx`)
  - Custom JS email regex (no native HTML5 interception)
  - Distinguishes `permission-denied` from network errors
- 3-step wizard at `/induction` with sticky progress header, Framer Motion transitions
- Section 1 — Personal/Business/Insurance with conditional insurance upload (`SectionPersonal.jsx`)
- Section 2 — Medical (15 Q) + HAVS (8 Q) using Yes/No pill toggles (`SectionMedical.jsx`)
- Section 3 — Declaration text + typed name + drawn signature canvas (`SectionSignature.jsx`, `SignaturePad.jsx`)
- File dropzones with size/type validation (`FileDropzone.jsx`)
- Auto-save with `interactedRef` gate (no flash on initial load) + unique mobile/desktop "Progress saved" testids
- Submission flow writes to all 4 Firestore collections, uploads 4 files + signature image to Storage, marks `access_codes` as used
- Success screen at `/success` with reference ID (`Success.jsx`)
- `SETUP_FIREBASE.md` — required Firestore + Storage rules and access-code seed instructions

## Rejection generates a fresh resubmission code (2026-02-09)
- Rejection PATCH now mints a new unique access code via `_new_unique_code()` and writes an `access_codes` doc with: `code`, `email`, `full_name`, `used:false`, `employee_id:""`, `invite_status:"resent_after_rejection"`, `created_at`, `invited_at`, `related_rejected_employee_id`, `rejection_reason`.
- `employee_summary` for the rejected record is updated with `resubmission_code`, `resubmission_requested: true`, `resubmission_access_code_id`, plus the existing `review_note` / `reviewed_at`.
- `rejection()` email template now embeds the **new access code**, the portal URL, the inductee's email, and the explicit instruction "Please complete the induction form again using the new access code."
- API response from `PATCH /api/admin/employees/{id}/review` now carries `new_access_code`, `new_access_code_id`, `portal_url`, `invitation_text` for HR display.
- `ReviewActionModal` stays open after a successful rejection and reveals the new code with **Copy code** and **Copy resubmission invite** buttons + ready-to-paste plain-text invitation.
- Toast and dashboard mirror the updated row: `resubmission_code` and `resubmission_requested` propagate immediately.

## Approval / Rejection workflow with confirmation modal (2026-02-09)
- New `ReviewActionModal.jsx` — shared modal with two modes:
  - **Approved**: shows inductee name + email, displays subject line preview ("PNC Induction Approved"), single confirm button.
  - **Rejected**: requires a non-empty rejection note (text area, Send button disabled while empty). Note appears verbatim inside the rejection email.
- AdminDashboard review-status dropdown now opens the modal for Approved / Rejected. "Pending Review" still fires inline (no email).
- `submitReview()` shows a clear toast: "Approved · approval email sent", "Rejected · rejection email sent", or "… · email failed to send" — pulled straight from the backend's `email_status` field.
- Backend: `update_review_status` now also writes `reviewed_at` (alongside `review_updated_at`). Email templates: approval subject is exactly "PNC Induction Approved"; rejection subject is "Additional information required for your PNC induction" with a clearly-styled note block. Both still log to `email_logs`. Resend key stays backend-only.
- Live-verified: approval email + rejection email (with note) both delivered to the Resend account inbox in test mode (`email_status: "sent"` in API response).

## Invite Employee + email workflow (2026-02-08)
- Backend: `POST /api/admin/invites` (Basic Auth) generates a unique `PNC-XXXX-XXXX` code, writes `access_codes` doc (code, email, full_name, used:false, employee_id:"", invited_at, invite_status), and — when `send_email=true` — sends a branded HTML email via Resend (`email_service.py`, `email_templates.py`). Returns the ready-to-paste plain-text invitation so HR can copy/paste into WhatsApp/SMS/Teams.
- `GET /api/admin/invites` (Basic Auth) lists all invitations newest-first.
- `PATCH /api/admin/employees/{id}/review` now also dispatches an Approval / Rejection email (with optional `review_note` shown to the inductee) on state transition. Idempotent: same `review_status` → no email re-sent.
- Audit log: every email (sent, redirected, skipped, failed) is recorded in a new `email_logs` Firestore collection.
- Resend secrets only in `backend/.env`: `RESEND_API_KEY`, `SENDER_EMAIL`, `RESEND_TEST_OVERRIDE_EMAIL` (test-mode delivery override, points at the Resend account owner until the PNC domain is verified), `PUBLIC_PORTAL_URL` (used as the link in the invitation).
- Frontend: `Invite Employee` button in the Employees toolbar opens a modal (`/app/frontend/src/components/InviteModal.jsx`) with **Send Email** + **Just Create Code** buttons. After creation: shows the generated code, copy buttons for the code and the full invitation text, and a status banner indicating whether the email was actually delivered (including Resend test-mode redirect notice).
- New `/admin/invitations` route (`AdminInvitations.jsx`) with table: Full Name, Email, Access Code, Invite Status (Sent / Code Only / Email Failed / Used), Used / Not Used pill, Invited At, Open record link when the invite has been used. Tabs nav between Employees and Invitations.

## HR Admin Portal + PNC spreadsheet alignment (2026-02-08)
- **Admin Portal** at `/admin` (`AdminLogin.jsx`) and `/admin/employees` (`AdminDashboard.jsx`) — gated by HTTP Basic Auth (same `ADMIN_USERNAME` / `ADMIN_PASSWORD` as backend). Credentials live in `sessionStorage` only.
- Table layout mirrors PNC's existing subcontractor spreadsheet column order exactly: Name → Date Of Birth → Address → Post Code → Phone → Email → NI → Induction Status → Medical Status → Driving Licence → Driving Licence Check → Passport → Right To Work → Proof Of Bank → Business Name → Account No → Sort Code → VAT → UTR → Review Status → PDF Link.
- Status pills (Complete / Awaiting Documents / Clear / Disclosed / Incomplete), Yes/No glyphs for DVLA, clickable "View" / "Open PDF" links for every document.
- Inline `Review Status` dropdown — HR can mark Approved / Rejected / Pending Review without leaving the table (PATCH /api/admin/employees/{id}/review).
- Top stats: Inductees, Pending Review, Approved, Awaiting Documents.
- Search + review-state filter; "Export CSV" button downloads via the authenticated endpoint.
- Backend derives `induction_status`, `medical_status`, `passport_status`, `driving_licence_status`, `bank_proof_status`, `insurance_certificate_status` on every finalize (`/app/backend/server.py`).
- CSV now uses the same human-readable headers and same column order as the dashboard (`CSV_SCHEMA` in `/app/backend/admin_routes.py`). Value formatting tightened: DVLA → Yes/No, Review Status → "Pending Review" / "Approved" / "Rejected".
- Tests updated (`/app/backend/tests/test_admin_routes.py`); 31/31 backend tests pass.

## Storage folder rename (2026-02-08)
- New submissions now upload under `employees/{slug(full_name)}-{employee_id}/` instead of the opaque `employees/{employee_id}/`. Slug rules: lowercase, accents stripped, non-alphanumeric removed, spaces collapsed to single `-`, trimmed.
- The frontend computes `storage_folder_path` after creating the `employees/` doc and writes it into `employee_documents.storage_folder_path` (`/app/frontend/src/lib/upload.js`, `/app/frontend/src/pages/Wizard.jsx`).
- The backend reads `storage_folder_path` from `employee_documents` on finalize; if missing (legacy records) it falls back **strictly** to `employees/{id}/` and does NOT migrate the legacy record. Legacy records keep their `employee_summary.storage_folder_path = None` so HR can identify them.
- PDF location follows the same folder: `{storage_folder_path}pdf/induction-{id}.pdf`.
- `storage_folder_path` is also exposed in the JSON list and CSV export (new column right after `employee_id`).
- Tests updated: 31/31 pass (`/app/backend/tests/test_admin_routes.py` CSV header mirror + Phase 2 regression).

## Phase 3 — HR Export System (2026-02-08)
- HTTP Basic Auth on `/api/admin/*` (`/app/backend/admin_routes.py`); creds in `backend/.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`). 401 with `WWW-Authenticate: Basic realm="PNC Admin"` when missing/wrong.
- `GET /api/admin/employees` — JSON list with AND-combined filters: `q` (name), `email`, `ni`, `company`, `review_status`, `date_from`, `date_to`, `limit`. Newest-first.
- `GET /api/admin/employees.csv` — streaming Excel/Sheets-compatible CSV (UTF-8 BOM, CRLF), filename `pnc-employees-YYYYMMDD-HHMM.csv`. Supports the same filters.
- `PATCH /api/admin/employees/{id}/review` — updates `review_status` (`pending_review` / `approved` / `rejected`) + optional `review_note`.
- `employee_summary` now includes `review_status` (default `pending_review`, **preserved across re-finalize**), `missing_documents` (auto-computed from file presence + insurance choice), `completed_modules` (currently `["induction"]`).
- `status` (system processing) and `review_status` (HR workflow) are kept separate per user request — clean future-proofing for HS forms / training records.
- Tests: 21/21 admin + 10/10 Phase 2 regression pass on iteration 3 (`/app/backend/tests/test_admin_routes.py`, `test_induction_finalize.py`).
- Credentials in `/app/memory/test_credentials.md`.
- FastAPI endpoint `POST /api/induction/finalize` (`/app/backend/server.py`) — wired into the React submission flow as a best-effort post-submit call
- `firebase_client.py` — initialises `firebase-admin` from `FIREBASE_SERVICE_ACCOUNT_B64`, returns Firestore + Storage clients
- `pdf_generator.py` — ReportLab A4 PDF with branded header band, kicker labels, kv-tables, colour-coded Yes/No tables, embedded signature image, declaration block, uploaded-documents table, page footers
- PDF uploaded to `employees/{id}/pdf/induction-{id}.pdf` with token-based stable download URL
- `employee_documents.pdf_url` (+ `pdf_path`, `pdf_generated_at`) updated
- New `employee_summary/{employee_id}` collection — denormalised master HR record with every key field flat + all file URLs (passport, driving_licence, insurance_certificate, bank_proof, signature, pdf). Replaces the CSV workflow. Admin-only by Firestore rules; Admin SDK on the backend bypasses rules
- Idempotent: re-running finalize overwrites the PDF at a deterministic path and merges into the same `employee_summary` doc
- Test suite at `/app/backend/tests/test_induction_finalize.py` — 10/10 pass on iteration 2

## Prioritized backlog
- **P1**
  - Email confirmation after submission (Resend / SendGrid) — send the inductee a PDF receipt and notify HR.
  - Optional admin-only `/api/access-codes/generate` endpoint to mint codes without using the Firebase Console.
- **P2**
  - Native CSV export endpoint that streams `employee_summary` as a downloadable CSV for spreadsheet workflows.
  - Resume induction by access code on a different device.
  - Photo capture (front camera) for passport / licence.
  - i18n (English + one second language).
  - File preview thumbnails before submission.
  - Performance hardening on `/api/induction/finalize`: wrap ReportLab in `asyncio.to_thread`, drop the extra Storage round-trip in `_make_public_url`.

## Next tasks
1. User confirms Firestore + Storage security rules from `SETUP_FIREBASE.md` are applied.
2. User seeds at least one access code in `access_codes` for end-to-end test.
3. Build the FastAPI PDF generation endpoint and wire it from the success path.
