# PNC Induction Portal — Domain & DNS Setup

_Companion to **DEPLOYMENT_GUIDE.md**_

Target outcome:
- `https://pnc-induction.co.uk` → Firebase Hosting (React SPA + same-origin `/api` rewrite to Cloud Run)
- `https://www.pnc-induction.co.uk` → 301 to apex (optional but recommended)
- `https://api.pnc-induction.co.uk` → Cloud Run direct (optional alternative to same-origin rewrite)
- Resend continues to send from `induction@pnc-induction.co.uk` with correct SPF / DKIM / DMARC

---

## 1. Cloudflare DNS records (final state)

You'll get the exact A / TXT values from each provider during setup. The shape is:

| Type | Name | Value (example) | Proxy | Purpose |
|---|---|---|---|---|
| A | `pnc-induction.co.uk` | `199.36.158.100` | **DNS only** (grey) | Firebase Hosting record #1 |
| A | `pnc-induction.co.uk` | `199.36.158.101` | **DNS only** (grey) | Firebase Hosting record #2 |
| CNAME | `www` | `pnc-induction.co.uk` | **DNS only** (grey) | Apex alias for www (Firebase will set it up to 301 → apex) |
| CNAME | `api` (optional) | `ghs.googlehosted.com.` | **DNS only** (grey) | Only if you map Cloud Run directly to a subdomain |
| TXT | `pnc-induction.co.uk` | `resend-verify=…` (from Resend) | n/a | Resend domain verification |
| TXT | `pnc-induction.co.uk` | `v=spf1 include:_spf.resend.com -all` | n/a | SPF |
| CNAME | `resend._domainkey` | `resend._domainkey.resend.com.` | **DNS only** (grey) | Resend DKIM |
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:dmarc@pnc-induction.co.uk; pct=100; adkim=r; aspf=r` | n/a | DMARC |
| CNAME | `bounce` (optional) | `feedback-smtp.eu-west-1.amazonses.com.` (Resend gives the exact value) | **DNS only** (grey) | Custom Return-Path |

> **Critical**: every Firebase / Google record **must be set to "DNS only" (grey cloud)** in Cloudflare. Proxying through Cloudflare (orange cloud) breaks Google's managed SSL certificate issuance. Keep proxy off until SSL is live; you can turn it on later for the apex only after Google certificate is active, but for max compatibility leave it off.

---

## 2. Apex (`pnc-induction.co.uk`) setup

Cloudflare allows A records at the apex (some registrars don't — Cloudflare does, that's why we're using it).

1. **Firebase Console → Hosting → Add custom domain** → enter `pnc-induction.co.uk`.
2. Firebase shows two A records — copy both IPs.
3. In Cloudflare → DNS → Add records:
   - Type **A**, Name `@`, Content first IP, Proxy **DNS only**.
   - Type **A**, Name `@`, Content second IP, Proxy **DNS only**.
4. Click **Verify** in Firebase. Status will move from "Needs setup" → "Pending" → "Connected" (5–60 min).
5. Firebase auto-provisions a managed SSL cert from Let's Encrypt. No action needed.

## 3. www subdomain (optional)

1. In Firebase Console → Hosting → Add custom domain → `www.pnc-induction.co.uk` → choose **Redirect to existing domain → `pnc-induction.co.uk`**.
2. Firebase gives a single CNAME target (usually a `ghs.googlehosted.com.` or similar). Add:
   - Type **CNAME**, Name `www`, Content the value Firebase gave you, Proxy **DNS only**.
3. After verification, `https://www.pnc-induction.co.uk` → 301 → `https://pnc-induction.co.uk`.

## 4. SSL setup

- **You don't generate certificates.** Firebase Hosting provisions a free managed Let's Encrypt cert automatically once DNS resolves. It auto-renews.
- If you also map `api.pnc-induction.co.uk` to Cloud Run directly, Google issues a **Google-managed** certificate the same way.
- **Cloudflare SSL mode must be "Full (strict)"** if you ever turn the orange cloud on — never "Flexible" (it'd downgrade traffic between Cloudflare and Firebase to HTTP).

## 5. Email DNS (Resend)

The four records you already added during Resend verification stay exactly as they are:

1. SPF TXT (`v=spf1 include:_spf.resend.com -all`)
2. DKIM CNAME (`resend._domainkey` → `resend._domainkey.resend.com.`)
3. Domain verification TXT (`resend-verify=…`)
4. _DMARC TXT — recommended addition_

For DMARC, paste into Cloudflare:

| Type | Name | Value |
|---|---|---|
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@pnc-induction.co.uk; pct=100; adkim=r; aspf=r` |

Start with `p=none` for 1–2 weeks to confirm clean reports, then tighten to `p=quarantine` and eventually `p=reject`.

## 6. Verification commands

After every change, verify from your laptop:

```bash
# Apex resolves to Firebase Hosting IPs
dig pnc-induction.co.uk +short

# www CNAME
dig www.pnc-induction.co.uk +short

# Resend SPF
dig TXT pnc-induction.co.uk +short | grep spf1

# DKIM
dig CNAME resend._domainkey.pnc-induction.co.uk +short

# DMARC
dig TXT _dmarc.pnc-induction.co.uk +short

# Final smoke test
curl -I https://pnc-induction.co.uk
# expect: HTTP/2 200, cert by Google Trust Services or Let's Encrypt
```

## 7. Emergency rollback to Emergent hosting

If something breaks badly during cutover and you need to revert to `induct-pro.emergent.host`:

1. In Cloudflare, **delete** the two A records for the apex.
2. Add an apex **CNAME flattening** (Cloudflare-specific feature) pointing to `induct-pro.emergent.host`.
3. DNS propagates in 1–5 min thanks to low TTLs (set TTL to "Auto" / 300 s in Cloudflare before cutover).
4. Email keeps working from Resend regardless of where the website lives.

Once you've fixed the issue, swap back to the A records and Firebase Hosting resumes.

---

## 8. Final DNS checklist (tick before go-live)

- [ ] Two apex A records present, both **DNS only**, Firebase status **Connected**.
- [ ] `www` CNAME present, **DNS only**, Firebase shows **Connected (Redirect)**.
- [ ] `dig pnc-induction.co.uk +short` returns the two Firebase IPs.
- [ ] `curl -I https://pnc-induction.co.uk` returns HTTP/2 200.
- [ ] Cloudflare SSL mode: **Full (strict)**.
- [ ] Cloudflare → SSL/TLS → Edge Certificates → **Always Use HTTPS: On**.
- [ ] Cloudflare → SSL/TLS → Edge Certificates → **Automatic HTTPS Rewrites: On**.
- [ ] Resend SPF / DKIM / DMARC all green in the Resend dashboard.
- [ ] Cloudflare TTL set to **Auto** (300 s) for fast emergency rollback.
