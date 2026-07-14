# Deployment Guide

> **This document has been reset as part of the Security & Trust Audit
> remediation.** All references to the previous, retired preview host and
> to the previous production domain have been removed. The go-live domain
> for the new deployment will be added below once it has been confirmed by
> PNC UNIQUE LTD.

## Overview

The Portal is a two-tier system:

| Tier | Technology | Hosted on |
| --- | --- | --- |
| Frontend (React) | Firebase Hosting | Same-origin as the API via a Firebase Hosting rewrite |
| Backend (FastAPI) | Google Cloud Run — region `europe-west2` | Exposed to Firebase Hosting only, not directly to the internet |
| Data | Firestore + Cloud Storage | Region `europe-west2` (London) |
| Email | Resend | Domain to be verified before go-live |

## Environment variables

See `backend/.env.example` (to be produced) for the full list. The current
staging deployment reads these from `backend/.env` and Cloud Run environment
variables in production. **The previously flagged host must not appear in
any of them.**

## Go-live checklist

- [ ] Create a fresh Firebase project (recommended — the existing project ID
      still contains legacy naming).
- [ ] Verify the production domain in Resend (SPF, DKIM, DMARC).
- [ ] Restrict `CORS_ORIGINS` in `backend/.env` to the production origin.
- [ ] Rotate `ADMIN_PASSWORD`, `RESEND_API_KEY` and the Firebase service
      account key that were visible in the staging environment.
- [ ] Set the production `PUBLIC_PORTAL_URL`.
- [ ] Confirm Firestore rules and Storage rules deployed match the ones in
      this repository.
