# Firebase Setup — Required Steps

The PNC Induction Portal connects directly to your existing Firebase project (`pnc-induction-portal`). For the portal to work end-to-end, you must:

## 1. Enable services in Firebase Console

- **Firestore Database** → enabled (already done).
- **Cloud Storage** → enabled. Make sure the default bucket is `pnc-induction-portal.firebasestorage.app`.

## 2. Configure Firestore Security Rules

In **Firebase Console → Firestore → Rules**, paste the rules below (or merge into your existing rules).

These rules let employees:
- Read access codes (so the gate can validate them)
- Create their own induction records (employees, medical_history, havs_questionnaires, employee_documents)
- Mark their access code as used

Admins still have full access via the Firebase Console with their Google account.

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Access codes: allow read (to validate by code) and updating the single doc to mark used
    match /access_codes/{code} {
      allow read: if true;
      allow update: if request.resource.data.diff(resource.data).changedKeys()
                       .hasOnly(['used','used_at','employee_id']);
      allow create, delete: if false; // admins only via console
    }

    // Employees: anyone can create their own record (no listing/reading by clients)
    match /employees/{id} {
      allow create: if true;
      allow read, update, delete: if false;
    }

    match /medical_history/{id} {
      allow create: if true;
      allow read, update, delete: if false;
    }
    match /havs_questionnaires/{id} {
      allow create: if true;
      allow read, update, delete: if false;
    }
    match /employee_documents/{id} {
      allow create: if true;
      allow read, update, delete: if false;
    }

    // employee_summary: admin-only (written by the backend via Admin SDK
    // which bypasses rules; clients have no access).
    match /employee_summary/{id} {
      allow read, write: if false;
    }
  }
}
```

> ⚠️ These are minimal rules to keep the public induction flow working without authenticating each subcontractor. If you want stronger guarantees, layer an App Check or Cloud Function in front of the writes.

## 3. Configure Storage Security Rules

In **Firebase Console → Storage → Rules**, paste:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /employees/{employeeId}/{allPaths=**} {
      // Allow new inductees to upload their documents and signature
      allow write: if request.resource.size < 10 * 1024 * 1024
                   && request.resource.contentType.matches('image/(jpeg|jpg|png)|application/pdf');
      // Reading the file URLs is required so the app can show a confirmation.
      allow read: if true;
    }
  }
}
```

## 4. Create access codes

Admins create one access code per inductee in the **`access_codes`** collection.

Document fields:

| Field | Type | Example |
|---|---|---|
| `code` | string | `PNC-AB12-CD34` |
| `email` | string | `new.hire@example.com` |
| `used` | boolean | `false` |
| `employee_id` | string | `null` (filled in after submission) |
| `created_at` | timestamp | Firestore server timestamp |
| `used_at` | timestamp | `null` (filled in after submission) |

You can create the document with the code as the document ID, or auto-ID — both work because the app queries by the `code` field.

## 5. PDF generation (Phase 2 — implemented)

After the form is submitted, the React app posts to `POST /api/induction/finalize` with the new `employee_id`. The FastAPI backend then:

1. Reads `employees`, `medical_history`, `havs_questionnaires`, `employee_documents` for that employee.
2. Downloads the drawn signature image from Storage and embeds it.
3. Generates a professional A4 PDF (ReportLab) with personal, business, insurance, medical, HAVS, declaration, and uploaded-documents sections.
4. Uploads the PDF to `employees/{employee_id}/pdf/induction-{employee_id}.pdf` and creates a stable download URL (token-based, no expiry).
5. Writes `pdf_url` (and `pdf_path`, `pdf_generated_at`) back into the matching `employee_documents` doc.
6. Creates/updates a denormalised **`employee_summary`** document keyed by `employee_id` — this is the **master HR record** that replaces the CSV workflow. It contains every key field plus the URLs of `passport`, `driving_licence`, `insurance_certificate`, `bank_proof`, `signature`, and `pdf`.

The `employee_summary` collection is admin-only — clients cannot read or write it; only the FastAPI backend (via the Admin SDK) and you (via the Firebase Console) have access.
