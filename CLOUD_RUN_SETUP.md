# Cloud Run Setup

> **Reset as part of the Security & Trust Audit remediation.** All
> references to the previous, retired preview host and to the previous
> production domain have been removed.

## Deploy

```bash
gcloud run deploy contractor-induction-api \
  --source ./backend \
  --region europe-west2 \
  --allow-unauthenticated=false \
  --set-env-vars="FIREBASE_STORAGE_BUCKET=<bucket>,ADMIN_USERNAME=<user>,SENDER_EMAIL=<verified>,CORS_ORIGINS=<origin>,APP_ENV=production"
```

Add `PUBLIC_PORTAL_URL` and `RESEND_API_KEY` as **secrets** (not env vars).

## Firebase Hosting rewrite

`firebase.json` already includes the rewrite from `/api/**` to the Cloud Run
service `contractor-induction-api` in `europe-west2`. Frontend calls
`/api/…` on the same origin as the Portal, so no CORS is needed in
production. The `CORS_ORIGINS` env var only matters if the API is called
from a different origin (e.g. for local development).
