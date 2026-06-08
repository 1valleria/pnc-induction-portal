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
- 3-step wizard at `/induction` with sticky progress header, Framer Motion transitions
- Section 1 — Personal/Business/Insurance with conditional insurance upload (`SectionPersonal.jsx`)
- Section 2 — Medical (15 Q) + HAVS (8 Q) using Yes/No pill toggles (`SectionMedical.jsx`)
- Section 3 — Declaration text + typed name + drawn signature canvas (`SectionSignature.jsx`, `SignaturePad.jsx`)
- File dropzones with size/type validation (`FileDropzone.jsx`)
- Auto-save with debounce + "Progress saved" badge (`autosave.js`)
- Submission flow writes to all 4 Firestore collections, uploads 4 files + signature image to Storage, marks `access_codes` as used
- Success screen at `/success` with reference ID (`Success.jsx`)
- Firebase Admin SDK service account stored as base64 in `backend/.env` for the upcoming PDF stage
- `SETUP_FIREBASE.md` — required Firestore + Storage rules and access-code seed instructions

## Prioritized backlog
- **P0**
  - Server-side PDF generation (FastAPI + reportlab) using the stored Admin SDK, upload to `employees/{id}/pdf/`, write URL to `employee_documents.pdf_url`
- **P1**
  - Email confirmation after submission (Resend / SendGrid)
  - Optional admin-only `/api/access-codes/generate` endpoint to mint codes without using the Firebase Console
- **P2**
  - CSV export endpoint that aggregates the 4 collections into a single master row per employee
  - Re-upload / resume by access code on a different device
  - Photo capture from the phone camera for passport/licence
  - i18n (English + one second language)
  - File preview thumbnails before submission

## Next tasks
1. User confirms Firestore + Storage security rules from `SETUP_FIREBASE.md` are applied.
2. User seeds at least one access code in `access_codes` for end-to-end test.
3. Build the FastAPI PDF generation endpoint and wire it from the success path.
