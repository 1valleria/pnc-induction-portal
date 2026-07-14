# Firebase Project Setup

> **Reset as part of the Security & Trust Audit remediation.** The
> previously blocked preview host must not appear anywhere in the new
> Firebase project.

## Required steps for a fresh deployment

1. Create a new Firebase project (or re-use the existing one — note that
   the existing project ID contains legacy naming and a rename requires
   data migration).
2. In Firebase Console → Project Settings → Service Accounts, generate a
   new private-key JSON. Base64-encode it and set
   `FIREBASE_SERVICE_ACCOUNT_B64` in `backend/.env`.
3. In Firebase Console → Storage, note the bucket name and set
   `FIREBASE_STORAGE_BUCKET` in `backend/.env`.
4. In Firebase Console → Firestore, seed one or more entries into the
   `access_codes` collection using the admin API (`POST /api/admin/invites`).
5. Deploy the rules bundled with this repository:

   ```bash
   firebase deploy --only firestore:rules,storage:rules
   ```

6. Verify the rules by attempting an anonymous read from the browser
   — it must fail.
