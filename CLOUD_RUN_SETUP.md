# PNC Induction Portal — Cloud Run Backend Setup

_Companion to **DEPLOYMENT_GUIDE.md** and **DOMAIN_SETUP.md**_

Backend = FastAPI (`/app/backend`) packaged as a container and deployed to Cloud Run in `europe-west2` (London). Cloud Run auto-scales to zero when idle and to many instances under load — typical monthly cost for the PNC volume: **£0–£5**.

---

## 1. Prerequisites

| Item | Where |
|---|---|
| Google Cloud project (any — you can reuse `pnc-induction-portal`) | https://console.cloud.google.com |
| `gcloud` CLI installed locally | `https://cloud.google.com/sdk/docs/install` |
| Billing enabled on the project | Console → Billing |
| APIs enabled: Cloud Run, Artifact Registry, Secret Manager, Cloud Build | `gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com` |
| Service account `firebase-admin` with `roles/datastore.user`, `roles/storage.objectAdmin`, `roles/secretmanager.secretAccessor` | Console → IAM |

> You can reuse the same Firebase Admin service account JSON you already have for `FIREBASE_SERVICE_ACCOUNT_B64` — it already has the right Firestore/Storage permissions. Just grant it `roles/secretmanager.secretAccessor` so Cloud Run can read secrets.

---

## 2. Dockerfile (drop into `/app/backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8001

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT (default 8080). Honour it.
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}
```

Add `/app/backend/.dockerignore`:

```
.env
__pycache__/
*.pyc
tests/
.pytest_cache/
.venv/
```

> `.env` is deliberately excluded — secrets come from Secret Manager at runtime, not baked into the image.

---

## 3. Store secrets in Google Secret Manager

```bash
# One-time: create each secret
gcloud secrets create FIREBASE_SERVICE_ACCOUNT_B64 --replication-policy=automatic
gcloud secrets create RESEND_API_KEY               --replication-policy=automatic
gcloud secrets create ADMIN_PASSWORD               --replication-policy=automatic

# Push the actual values (use --data-file=- to avoid history)
gcloud secrets versions add FIREBASE_SERVICE_ACCOUNT_B64 --data-file=/tmp/sa.b64
gcloud secrets versions add RESEND_API_KEY               --data-file=- <<<'re_REAL_KEY_HERE'
gcloud secrets versions add ADMIN_PASSWORD               --data-file=- <<<'NEW_STRONG_PASSWORD'

# Allow the Cloud Run service account to read them
SVC="$(gcloud iam service-accounts list --format='value(email)' --filter='displayName:Cloud Run')"
for s in FIREBASE_SERVICE_ACCOUNT_B64 RESEND_API_KEY ADMIN_PASSWORD; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:$SVC" \
    --role="roles/secretmanager.secretAccessor"
done
```

Delete `/tmp/sa.b64` after you're done. **Never** commit secret values to git.

---

## 4. Build and push the image

From the repo root:

```bash
PROJECT=pnc-induction-portal
REGION=europe-west2
REPO=pnc

# One-time: create the Artifact Registry repo
gcloud artifacts repositories create $REPO \
  --repository-format=docker --location=$REGION --description="PNC images"

# Build + push (Cloud Build does it server-side; no local Docker daemon needed)
gcloud builds submit ./backend \
  --tag $REGION-docker.pkg.dev/$PROJECT/$REPO/induction-api:v1
```

---

## 5. Deploy to Cloud Run

```bash
gcloud run deploy pnc-induction-api \
  --image $REGION-docker.pkg.dev/$PROJECT/$REPO/induction-api:v1 \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 5 \
  --concurrency 40 \
  --timeout 60 \
  --set-env-vars="FIREBASE_STORAGE_BUCKET=pnc-induction-portal.firebasestorage.app,ADMIN_USERNAME=pnc-admin,SENDER_EMAIL=induction@pnc-induction.co.uk,PUBLIC_PORTAL_URL=https://pnc-induction.co.uk,CORS_ORIGINS=https://pnc-induction.co.uk" \
  --set-secrets="FIREBASE_SERVICE_ACCOUNT_B64=FIREBASE_SERVICE_ACCOUNT_B64:latest,RESEND_API_KEY=RESEND_API_KEY:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest"
```

After ~60 seconds Cloud Run returns the service URL (e.g. `https://pnc-induction-api-abcdefg-nw.a.run.app`). Test it:

```bash
curl https://pnc-induction-api-abcdefg-nw.a.run.app/api/health
# expect: {"status":"ok","service":"pnc-induction-api"}
```

---

## 6. Two options for routing `/api/*`

### Option A (recommended) — Firebase Hosting same-origin rewrite

Add the rewrite block already shown in `DEPLOYMENT_GUIDE.md → firebase.json`. **No custom domain on Cloud Run needed.** Frontend calls `https://pnc-induction.co.uk/api/...`, Firebase Hosting proxies to the Cloud Run service by `serviceId`. Simpler, no extra DNS, no CORS.

Set frontend:
```
REACT_APP_BACKEND_URL=https://pnc-induction.co.uk
```

### Option B — Cloud Run custom domain `api.pnc-induction.co.uk`

If you'd rather expose the API on its own subdomain:

1. Cloud Run console → service → **Manage Custom Domains** → Add `api.pnc-induction.co.uk`.
2. Verify domain ownership (Google asks for one TXT record — paste into Cloudflare DNS, **DNS only**).
3. After verification, Google gives you a CNAME target (`ghs.googlehosted.com.`). Add as `api` CNAME, **DNS only**.
4. Wait for Google-managed certificate (5–60 min).

Set frontend:
```
REACT_APP_BACKEND_URL=https://api.pnc-induction.co.uk
CORS_ORIGINS=https://pnc-induction.co.uk
```

Option B is more conventional but adds a DNS record and CORS configuration. Choose A unless your team has a strong reason to split origins.

---

## 7. Continuous deploys (optional but recommended)

Hook this up so any push to `main` rebuilds and ships:

```bash
gcloud run deploy pnc-induction-api \
  --source ./backend \
  --region $REGION \
  --trigger-branch=main \
  --trigger-repo=github_org/pnc-induction
```

Or use Cloud Build triggers via the console — point it at the GitHub repo you exported from Emergent. Frontend gets the same treatment via **GitHub Actions → `firebase deploy --only hosting`**.

---

## 8. Cost expectations (production volume = a few inductees/day)

| Component | Free tier covers you | Cost at PNC volume |
|---|---|---|
| Cloud Run | 2M req/month + 360k GB-s + 180k vCPU-s | ~£0 |
| Cloud Build | 120 build-min/day | ~£0 |
| Artifact Registry | 0.5 GB | ~£0 |
| Secret Manager | 10k access/month | ~£0 |
| Firebase Hosting | 10 GB transfer + 360 MB/day storage | ~£0 |
| Firebase Firestore | 50k reads / 20k writes / day | ~£0 |
| Firebase Storage | 5 GB stored, 1 GB/day egress | ~£0 |
| Resend | 3,000 emails/month | ~£0 (≈ $20/mo at 10k+ emails) |

Expect **£0–£5/month** until you scale to thousands of inductees. The big variable is Resend volume.

---

## 9. Monitoring

- **Cloud Run console → Logs** — every request, every error, structured.
- Set alerts: Console → Monitoring → Alerts → "Cloud Run service errors > 5 in 5 min" / "Latency p95 > 2s".
- Resend dashboard — bounces, complaints, deliverability per recipient.
- Firebase Console → Performance + Crashlytics if you ever add the SDK.

---

## 10. Final pre-launch checklist (Cloud Run side)

- [ ] Dockerfile + .dockerignore committed.
- [ ] Image built and pushed to Artifact Registry.
- [ ] Three secrets created in Secret Manager with current production values.
- [ ] Cloud Run service deployed, `--allow-unauthenticated` set.
- [ ] `curl /api/health` returns 200 from the Cloud Run URL.
- [ ] `curl -u pnc-admin:… /api/admin/employees` returns 200 from the Cloud Run URL.
- [ ] Frontend `firebase.json` rewrite or DNS CNAME for `api.` confirmed.
- [ ] CORS_ORIGINS set to the production frontend URL.
- [ ] Concurrency / instance limits set (40 / 5 are good starting points).
- [ ] Cloud Build trigger (or GitHub Action) wired up if you want auto-deploys.

When all boxes are ticked, follow **DEPLOYMENT_GUIDE.md → Step 8 Smoke test** to verify end-to-end and then **Step 9 Decommission Emergent**.
