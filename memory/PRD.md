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
