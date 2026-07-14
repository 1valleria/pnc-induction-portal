# Production Readiness

> **Reset as part of the Security & Trust Audit remediation.**

Before any production go-live:

- [ ] All Firestore reads and writes go through the backend Admin SDK
      (client-side Firestore is now deny-by-default in `firestore.rules`).
- [ ] Cloud Storage rules deny read access from the browser; download
      tokens are minted server-side (`_make_public_url` in
      `backend/server.py`).
- [ ] `CORS_ORIGINS` restricted to the production origin.
- [ ] FastAPI `/docs`, `/redoc`, `/openapi.json` disabled
      (`APP_ENV=production`).
- [ ] `RESEND_API_KEY` configured with a domain-verified sender.
- [ ] `ADMIN_PASSWORD` rotated and stored only in secret manager.
- [ ] Security headers (`Content-Security-Policy`, `HSTS`, `X-Frame-Options`,
      `Referrer-Policy`, `Permissions-Policy`) verified against the
      deployed host.
- [ ] Corporate identity placeholders in the footer and legal pages
      populated with the real company number, registered office and
      contact email.
- [ ] Data-protection contact and ICO registration number added to the
      Privacy Notice.
- [ ] Manual regression run on: access-code login, wizard submission,
      document upload, signature, PDF generation, admin login, admin
      review approval, admin review rejection, invitation email
      (once the API key is re-enabled).
