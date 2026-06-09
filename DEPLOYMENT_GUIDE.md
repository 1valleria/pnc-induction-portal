# PNC Induction Portal — Migration to `pnc-induction.co.uk`

_Last updated: 2026-02-09_

This is the master plan to move the portal from the Emergent-hosted preview/production URLs to your own domain on Firebase Hosting + Google Cloud Run. It assumes the **Firestore + Storage data stays exactly where it is** (`pnc-induction-portal` project) — only the hosting layer changes.

> Three companion docs to read alongside this one:
> - **DOMAIN_SETUP.md** — exact Cloudflare DNS records, root vs www, SSL.
> - **CLOUD_RUN_SETUP.md** — backend deployment, secrets, custom domain mapping.
> - **DEPLOYMENT_GUIDE.md** _(this file)_ — the end-to-end runbook.

---

## Target architecture

```
                  https://pnc-induction.co.uk
                            │
                            ▼
                  Firebase Hosting (CDN)
                  serves the React bundle
                            │
                            │ /api/* rewrite
                            ▼
            Google Cloud Run — FastAPI container
                            │
                ┌───────────┼────────────┐
                ▼           ▼            ▼
          Firestore     Storage      Resend
        (existing)    (existing)   (existing)
```

All four right-side services already exist on your Firebase project / Resend account — no migration there.

---

## Step-by-step migration (≈ 90 minutes)

### Step 1 — Build a deployable backend container
- Add `Dockerfile` + `.dockerignore` (templates in **CLOUD_RUN_SETUP.md**).
- Tag the firebase-admin service-account JSON as a Secret in **Google Secret Manager** rather than baking it into `.env`.
- Push to Artifact Registry: `gcloud builds submit --tag europe-west2-docker.pkg.dev/PROJECT/pnc/induction-api`.

### Step 2 — Deploy to Cloud Run
- `gcloud run deploy pnc-induction-api --image …` with the env vars listed in §"Environment variables" below.
- Region: `europe-west2` (London) — same as Firestore for lowest latency.
- Allow unauthenticated traffic (your app already enforces Basic Auth on admin routes).

### Step 3 — Map a custom subdomain to the Cloud Run service
- `api.pnc-induction.co.uk` → Cloud Run. See **CLOUD_RUN_SETUP.md → Custom domain**.
- Google issues the LE / managed certificate automatically once DNS resolves.

### Step 4 — Build a production frontend bundle
- In `/app/frontend/.env.production` set:
  ```
  REACT_APP_BACKEND_URL=https://api.pnc-induction.co.uk
  REACT_APP_FIREBASE_API_KEY=…  (same as today)
  REACT_APP_FIREBASE_AUTH_DOMAIN=pnc-induction-portal.firebaseapp.com
  REACT_APP_FIREBASE_PROJECT_ID=pnc-induction-portal
  REACT_APP_FIREBASE_STORAGE_BUCKET=pnc-induction-portal.firebasestorage.app
  REACT_APP_FIREBASE_MESSAGING_SENDER_ID=38305417681
  REACT_APP_FIREBASE_APP_ID=1:38305417681:web:0ed699f164093721c878f0
  ```
- `cd frontend && yarn build` → outputs `frontend/build/`.

### Step 5 — Deploy the static bundle to Firebase Hosting
- `firebase init hosting` (one-time):
  - Public dir: `frontend/build`
  - Single-page app: **Yes**
  - GitHub auto-deploy: optional but recommended
- `firebase.json` (template in **DEPLOYMENT_GUIDE.md → firebase.json**) adds an `/api/**` rewrite to Cloud Run so the React app keeps using same-origin URLs.
- `firebase deploy --only hosting`.

### Step 6 — Point your domain at Firebase Hosting
- Firebase Console → Hosting → Add custom domain → `pnc-induction.co.uk` and `www.pnc-induction.co.uk`.
- Firebase shows two A records (or one CNAME for www) — paste them into Cloudflare as described in **DOMAIN_SETUP.md**.
- Wait 5–60 minutes for DNS / SSL.

### Step 7 — Update environment variables that reference the public URL
- Cloud Run: `gcloud run services update pnc-induction-api --update-env-vars PUBLIC_PORTAL_URL=https://pnc-induction.co.uk`.
- Frontend was already rebuilt with the new `REACT_APP_BACKEND_URL`; nothing else changes on the React side.

### Step 8 — Smoke test
1. `curl https://api.pnc-induction.co.uk/api/health` → `{"status":"ok",…}`
2. `curl -u pnc-admin:… https://api.pnc-induction.co.uk/api/admin/employees` → 200 with items.
3. `https://pnc-induction.co.uk/admin` → login screen renders, no Emergent watermark.
4. End-to-end: invite → submit → PDF → approve → real email arrives at the real recipient.

### Step 9 — Decommission the Emergent host (only after step 8 passes)
- Pause / delete the Emergent production deployment.
- Optionally keep the Emergent **preview** environment for staging.

---

## Environment variables (final)

### Cloud Run (backend)
```
FIREBASE_SERVICE_ACCOUNT_B64   ← stored in Secret Manager, mounted at deploy
FIREBASE_STORAGE_BUCKET=pnc-induction-portal.firebasestorage.app
ADMIN_USERNAME=pnc-admin
ADMIN_PASSWORD=<rotate before go-live>
RESEND_API_KEY=re_…             ← also from Secret Manager
SENDER_EMAIL=induction@pnc-induction.co.uk
PUBLIC_PORTAL_URL=https://pnc-induction.co.uk
CORS_ORIGINS=https://pnc-induction.co.uk
```

### Firebase Hosting (frontend, baked into the bundle at build time)
```
REACT_APP_BACKEND_URL=https://api.pnc-induction.co.uk
REACT_APP_FIREBASE_*  (same values you already have)
```

> **Never** put `RESEND_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_B64` or `ADMIN_PASSWORD` in the frontend `.env` — anything prefixed with `REACT_APP_` is embedded into the JS bundle and visible to anyone who opens DevTools.

---

## `firebase.json` (frontend rewrites + cache headers)

```json
{
  "hosting": {
    "public": "build",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      { "source": "/api/**", "run": {
          "serviceId": "pnc-induction-api",
          "region":    "europe-west2"
        }
      },
      { "source": "**", "destination": "/index.html" }
    ],
    "headers": [
      { "source": "**/*.@(js|css)", "headers": [
          { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
        ]
      },
      { "source": "/index.html", "headers": [
          { "key": "Cache-Control", "value": "no-cache" }
        ]
      }
    ]
  }
}
```

The Firebase Hosting Cloud Run rewrite means **the frontend never needs to know the Cloud Run URL** — it calls `/api/...` on the same origin and Firebase Hosting reverse-proxies to your container. Side benefits:
- No CORS headaches.
- TLS terminates at Google's edge globally.
- You can swap Cloud Run regions later without changing the frontend.

> If you'd rather use a separate `api.pnc-induction.co.uk` hostname instead of the same-origin proxy (option above), follow **CLOUD_RUN_SETUP.md → Custom domain mapping**. Both patterns work; the same-origin rewrite is simpler.

---

## Rollback plan

| Scenario | Action | Time to recover |
|---|---|---|
| Frontend deploy broken | `firebase hosting:rollback` (one click in console; or `firebase hosting:channel:deploy`) | 30 s |
| Cloud Run release broken | `gcloud run services update-traffic pnc-induction-api --to-revisions=PREVIOUS=100` | 30 s |
| DNS misconfigured / certificate stuck | Re-point Cloudflare to the Emergent host (instructions in DOMAIN_SETUP.md → "Emergency rollback to Emergent") | 5–60 min DNS TTL |
| Firestore data corruption | Firebase Console → Firestore → **Import / Export** → restore from the daily export bucket | up to 1 h |
| Email failures only | Switch `SENDER_EMAIL` back to `onboarding@resend.dev` and add `RESEND_TEST_OVERRIDE_EMAIL` temporarily — runs in safe mode until DNS / DKIM is fixed | 5 min |

**Key principle:** because the data lives in Firebase and the Emergent deployment is read-only standby, you can revert hosting at any time without losing a single record.

---

## What's NOT changing during migration

- Firebase project ID (`pnc-induction-portal`).
- Firestore collections, rules, data.
- Storage bucket, rules, files.
- Resend account, API key, verified domain (`pnc-induction.co.uk`).
- Admin Basic Auth credentials.
- Code logic — only environment values are touched.

This is intentional: the migration is a **hosting swap**, not a re-platforming.

---

See **DOMAIN_SETUP.md** next for the Cloudflare side, then **CLOUD_RUN_SETUP.md** for the backend build.
