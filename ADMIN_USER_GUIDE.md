# PNC Induction System — Admin User Guide

_Last updated: 2026-02-09 · Version 1.0_

---

## 1. Introduction

### What this system does

The PNC Induction Portal replaces the old Google Form → Google Sheet → manual CSV → manual filing workflow with a single, digital, mobile-first system for onboarding subcontractors.

Every subcontractor:

1. Receives a unique one-time **access code** from PNC HR.
2. Completes a 3-step digital induction on their phone.
3. Uploads passport, driving licence, bank proof and (if applicable) insurance certificate.
4. Signs digitally (typed name + drawn signature).
5. Automatically gets a professional PDF generated and filed in Firebase Storage.

You — the admin — control the full lifecycle from the **PNC HR Admin Portal**.

### High-level workflow

```
HR invites → inductee receives code → completes form → record + PDF saved
                              ↓
                  HR reviews in the Admin Portal
                              ↓
                ┌─────────────┴─────────────┐
            Approved                    Rejected
              ↓                            ↓
       Approval email           Rejection email + NEW access code
                                          ↓
                                 Inductee resubmits with new code
```

---

## 2. Admin Login

### Accessing the portal

- Production URL: **https://induct-pro.emergent.host/admin**
- Open it in any modern browser. Mobile is supported but the data table is best on desktop / tablet landscape.

### Signing in

1. You will see the **PNC HR Admin** sign-in screen.
2. Enter your **admin username** and **password** (provided separately by your IT contact).
3. Click **Sign in**.

> **Tip — keep your credentials safe.** The portal exposes NI numbers, bank details and medical information. Never share the password by email or paste it into chat tools. Sign out when you're done by clicking the door icon in the top-right.

If you get "Invalid username or password", double-check capitalisation. After 3 failed attempts give it a minute before trying again.

---

## 3. Inviting a new subcontractor

From the **Employees** page, click **Invite Employee** in the top toolbar.

A modal opens with two fields:

| Field | Required | Notes |
|---|---|---|
| Full Name | ✓ | Used in the email greeting and the access-code record |
| Email Address | only if you want to send an email | If omitted you can still create a code to share by SMS / WhatsApp / Teams |

You then have two buttons:

### Option A — Send Email

Click **Send Email** to:

1. Generate a unique access code (format `PNC-XXXX-XXXX`).
2. Save it in Firestore.
3. Email the inductee a branded invitation containing their name, the portal URL, their email, and the code.

A success toast appears: "Invitation sent to john@example.com".

### Option B — Just Create Code

Click **Just Create Code** if the inductee doesn't have email or you prefer to message the code yourself.

After either action the modal shows:

- **The generated code** with a **Copy code** button.
- A **ready-to-paste invitation** (multi-line text including portal URL, email and code) with a **Copy invitation** button.

Paste the invitation straight into WhatsApp, SMS, Teams or your email client.

### Reviewing all invitations

Click the **Invitations** tab in the top nav. You'll see every code ever created with:

- **Full Name, Email, Access Code** — what you sent.
- **Invite Status** — Sent / Code Only / Email Failed / Used.
- **Used / Not Used** — whether the inductee has completed the form.
- **Invited At** — timestamp of creation.
- **Open record** — appears once the code is used; jumps to the inductee's row in Employees.

---

## 4. Reviewing inductions

### Finding an employee

From the **Employees** page:

- Use the **search box** at the top to filter by name, email, NI number, company name or phone (substring match, case-insensitive).
- Use the **review state dropdown** to narrow by Pending Review / Approved / Rejected.

The header counters show totals at a glance: Inductees, Pending Review, Approved, Awaiting Documents.

### Reading the row

Columns follow PNC's existing subcontractor spreadsheet order so HR can stop using the old workflow immediately:

| Column | What it means |
|---|---|
| **Name / DOB / Address / Post Code / Phone / Email / NI** | Personal section the inductee filled in. |
| **Induction Status** | `Complete` (all docs uploaded and PDF generated), `Awaiting Documents` (some required file missing), `Pending` (form created but PDF not yet generated). |
| **Medical Status** | `Clear` (every medical question answered No), `Disclosed` (one or more Yes — HR review recommended), `Incomplete` (any unanswered). |
| **Driving Licence / Passport / Proof Of Bank** | Click "View" to open the uploaded file in a new tab. |
| **Driving Licence Check** | Yes / No — answer to the DVLA check question. |
| **Right To Work** | The right-to-work share code. |
| **Business Name / Account / Sort Code / VAT / UTR** | Business details. |
| **Review Status** | Inline dropdown to Approve / Reject (see next section). |
| **PDF Link** | Opens the full induction PDF (passport, business, medical, HAVS, signature, declaration). |

### Viewing documents

Click any **View** link in the Driving Licence / Passport / Proof Of Bank columns. The document opens in a new browser tab, served straight from Firebase Storage.

### Opening the induction PDF

Click **Open PDF** in the rightmost column. The professionally formatted A4 induction record opens in a new tab — print or download as needed.

---

## 5. Approving an induction

1. Find the inductee's row.
2. In the **Review Status** column, change the dropdown to **Approved**.
3. A green confirmation modal appears showing the inductee's name, email and the subject line preview ("**PNC Induction Approved**").
4. Click **Send Approval Email**.

What happens automatically:

- `review_status` set to `approved`
- `reviewed_at` timestamp saved
- Approval email sent to the inductee
- Email recorded in `email_logs`

Toast: "Approved · approval email sent".

---

## 6. Rejecting an induction

Rejection always generates a **fresh one-time access code** so the inductee can resubmit. The old code is never reused.

1. Change the **Review Status** dropdown to **Rejected**.
2. A red modal opens asking for a **reason / comment**. This is **required**.
3. Type a clear note — *e.g. "Driving licence has expired — please re-upload a current copy."*
4. Click **Send Rejection Email**.

What happens automatically:

- `review_status` set to `rejected`, `review_note` saved, `reviewed_at` saved
- A new unique access code is created with `invite_status: resent_after_rejection`, linked to the original record via `related_rejected_employee_id`
- `employee_summary` updated with `resubmission_code` and `resubmission_requested: true`
- Rejection email sent containing your reason, the **new access code**, the portal URL and the explicit instruction "Please complete the induction form again using the new access code."
- Email recorded in `email_logs`

The modal stays open and now shows:

- The **new access code** with a **Copy code** button.
- The **ready-to-paste resubmission invitation** with a **Copy resubmission invite** button.

You can paste this directly into WhatsApp / SMS / Teams if the inductee has no email or the email goes to spam.

Toast: "Rejection email sent and new access code generated."

---

## 7. Employee records — understanding the indicators

### Status pills

| Pill | Colour | Meaning |
|---|---|---|
| Complete | green | All required documents present, PDF generated, ready for review. |
| Awaiting Documents | amber | One or more required documents missing — check the `missing_documents` field. |
| Pending | grey | Record exists but PDF not yet generated (rare; usually because finalize failed). |
| Clear | green | Medical: every question answered No. |
| Disclosed | amber | Medical: one or more Yes — HR should review the medical details in the PDF. |
| Incomplete | red | Medical: at least one question unanswered. |
| Pending Review | grey | HR has not yet approved or rejected. |
| Approved | green | HR has approved; subcontractor is cleared. |
| Rejected | red | HR has rejected; resubmission code issued. |

### Document indicators (CSV export)

Each document column shows either a clickable URL (file uploaded) or an empty cell (missing). The CSV mirrors this exactly so Excel makes the missing rows visible at a glance.

---

## 8. Invitations — understanding the states

| Status | Meaning |
|---|---|
| **Sent** | HR sent the invitation email; inductee has not yet started. |
| **Code Only** | HR generated the code without sending email (shared manually). |
| **Email Failed** | Resend rejected the send. The code is still valid — share it manually. |
| **Used** | Inductee completed the induction with this code. The `employee_id` column will jump to their record. |
| **Resent After Rejection** | Code was minted automatically because HR rejected a previous submission. |

---

## 9. CSV export

1. Click **Export CSV** in the Employees toolbar.
2. The file downloads as `pnc-employees-YYYY-MM-DD.csv`.
3. Open it in Excel or Google Sheets — every column matches the on-screen table.

To export a **filtered** set, apply the search box and/or review-state filter first; the CSV honours both.

### Column reference

`Name, Date Of Birth, Address, Post Code, Phone Number, Email Address, NI Number, Induction Status, Medical Status, Driving Licence, Driving Licence Check, Passport, Right To Work, Proof Of Bank, Business Name, Account Number, Sort Code, VAT Number, UTR, Review Status, PDF Link, Employee ID, Submitted At`

Document URL columns (Driving Licence, Passport, Proof Of Bank, PDF Link) are clickable in Excel — click to open the file straight from Firebase Storage.

---

## 10. Troubleshooting

### "The inductee says they lost their access code"

1. Open the **Invitations** tab.
2. Find their entry (search by name or email).
3. If `Used = No`, copy the code and re-send it manually via WhatsApp / SMS.
4. If `Used = Yes`, the code is spent — generate a new invite via **Invite Employee**.

### "An induction shows Awaiting Documents"

Click into the row and check the document columns. Any missing item is empty. Tell the inductee which file is missing and either:

- Reject with a note asking them to re-upload (preferred — they'll get a new code), or
- Ask them to email the file to HR if a single doc is missing and you want to attach it manually in Firebase Storage.

### "The inductee says they can't log in / their code is invalid"

Possible causes:

1. Code already used — generate a fresh one (Invite Employee).
2. Code typed with `0` instead of `O` — codes only use the safe alphabet `2-9, A-Z minus 0,O,1,I,L`.
3. They used the wrong email — every code is bound to a specific email; check the Invitations tab.

### "The invitation email did not arrive"

1. Ask them to check spam.
2. Check the **Invitations** tab — does the row show `Email Failed`?
3. Check the `email_logs` collection in Firebase Console; the latest log entry will explain the error.
4. As a workaround: copy the invitation and paste into WhatsApp / SMS / Teams.

**Note:** during Resend's test mode the email always goes to the Resend account owner, not the real inductee. Once your PNC domain is verified this stops being an issue.

---

## 11. System Architecture (high level)

```
┌──────────────────────┐        ┌──────────────────────┐
│   Subcontractor      │        │      PNC HR          │
│  (phone / desktop)   │        │   (admin browser)    │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           ▼                               ▼
    Induction Portal               Admin Portal (/admin)
       (React)                          (React)
           │                               │
           ▼                               ▼
   Firebase (Web SDK)        Backend API (FastAPI)
   - Firestore writes              - Basic Auth
   - Storage uploads               - Admin endpoints
                                   - Resend email
                                          │
                                          ▼
                                Firebase (Admin SDK)
                                - Firestore reads
                                - Storage signed URLs
                                - PDF generation
```

- **Firebase Firestore** — primary database; holds employees, medical, HAVS, documents, summaries, access codes, email logs.
- **Firebase Storage** — file storage for passports, driving licences, bank proofs, insurance certificates, signatures, and the generated PDF.
- **FastAPI backend** — runs the PDF generator (ReportLab), the admin endpoints and the email sender (Resend).
- **Admin Portal** — React app served from the same domain; talks to the FastAPI backend via HTTP Basic Auth.

---

_End of guide. For technical support, contact your PNC IT or system administrator._
