# Custom Domain Setup

> **Reset as part of the Security & Trust Audit remediation.** The
> previously flagged host has been retired and must not be reintroduced
> anywhere in this repository. The final production domain for the
> re-deployed Portal will be added here once confirmed.

When the production domain is confirmed:

1. Add the domain to Firebase Hosting (Console → Hosting → Add custom
   domain). Follow the DNS instructions Firebase provides.
2. Add SPF / DKIM / DMARC for the sending domain in Resend.
3. Update `PUBLIC_PORTAL_URL`, `SENDER_EMAIL` and `CORS_ORIGINS` in the
   backend environment.
4. Verify `curl -I https://<domain>` returns `HTTP/2 200` and the CSP /
   HSTS headers from `firebase.json` are present.
