"""HTML email templates for PNC UNIQUE LTD HR notifications.

All user-supplied strings (`full_name`, `note`, `email`, `company_name`,
`portal_url`, `code`) are passed through ``html.escape`` before being
interpolated into HTML, so the templates are XSS-safe even if an inductee
or admin submits values containing angle brackets or quotes. `portal_url`
is additionally validated against an http(s) allow-list before being used
as an anchor href.

Plain inline-CSS, tables-based — kept simple so they render cleanly in
Outlook, Gmail and Apple Mail. No external CSS, no images.
"""
from __future__ import annotations

import html as _html

BRAND = "#166534"
INK = "#1C1917"
MUTED = "#57534E"
SOFT = "#FAFAF9"
LINE = "#E7E5E4"


def _e(value) -> str:
    """HTML-escape a possibly-None value; empty string for None."""
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)


def _safe_href(url) -> str:
    """Escape and enforce http(s) scheme on any URL used as an anchor href.

    Returns an empty string if the URL is not http(s), so the resulting
    ``href=""`` renders as an inert link instead of a ``javascript:``
    injection vector.
    """
    if not url:
        return ""
    s = str(url).strip()
    lower = s.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return ""
    return _html.escape(s, quote=True)


def _shell(*, preheader: str, body_html: str) -> str:
    ph = _e(preheader)
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Contractor Induction</title>
</head>
<body style="margin:0;padding:0;background:{SOFT};font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{INK};">
  <span style="display:none;visibility:hidden;opacity:0;color:transparent;height:0;width:0;">{ph}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;border:1px solid {LINE};border-radius:14px;overflow:hidden;">
        <tr><td style="background:{BRAND};padding:20px 28px;">
          <div style="color:#BBF7D0;font-size:11px;letter-spacing:.18em;font-weight:700;">PNC UNIQUE LTD &middot; CONTRACTOR INDUCTION</div>
        </td></tr>
        <tr><td style="padding:28px;">
          {body_html}
          <p style="margin:28px 0 0;color:{MUTED};font-size:12px;line-height:1.5;">
            If you weren&#39;t expecting this email, please ignore it or contact PNC UNIQUE LTD HR.
          </p>
        </td></tr>
      </table>
      <div style="color:{MUTED};font-size:11px;margin-top:16px;">&copy; PNC UNIQUE LTD &middot; confidential</div>
    </td></tr>
  </table>
</body>
</html>"""


def invitation(full_name: str, portal_url: str, email: str, code: str) -> tuple[str, str]:
    subject = "Your contractor induction \u2014 action required"
    preheader = "Complete your digital induction in about 5 minutes."
    href = _safe_href(portal_url)
    portal_text = _e(portal_url)
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Hi {_e(full_name) or 'there'},</h1>
      <p style="margin:0 0 18px;color:{MUTED};font-size:14px;line-height:1.55;">
        You&#39;ve been invited to complete your PNC UNIQUE LTD subcontractor induction. The form takes about 5 minutes on a phone and only needs to be done once.
      </p>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;margin:14px 0;">
        <tr><td style="padding:18px 20px;">
          <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;">Email address</div>
          <div style="font-weight:600;color:{INK};font-size:15px;margin-top:2px;">{_e(email)}</div>
          <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin-top:12px;">Access code</div>
          <div style="font-weight:700;font-family:'SFMono-Regular',Menlo,Consolas,monospace;color:{INK};font-size:18px;margin-top:2px;">{_e(code)}</div>
        </td></tr>
      </table>

      <p style="margin:18px 0 8px;">
        <a href="{href}" style="background:{BRAND};color:#FFFFFF;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:10px;display:inline-block;font-size:14px;">Start my induction &rarr;</a>
      </p>
      <p style="margin:14px 0 0;color:{MUTED};font-size:12px;">
        Direct link: <a href="{href}" style="color:{BRAND};">{portal_text}</a>
      </p>
    """
    return subject, _shell(preheader=preheader, body_html=body)


def _employee_block(employee_name: str, employee_email: str, company_name: str | None) -> str:
    rows = [("Inductee", _e(employee_name) or "\u2014"), ("Email", _e(employee_email) or "\u2014")]
    if company_name:
        rows.append(("Company", _e(company_name)))
    body = "".join(
        f'<div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;">{lbl}</div>'
        f'<div style="font-weight:600;color:{INK};font-size:15px;margin:2px 0 10px;">{val}</div>'
        for lbl, val in rows
    )
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;margin:14px 0;">
      <tr><td style="padding:16px 20px;">{body}</td></tr>
    </table>
    """


def manager_approval(employee_name: str, employee_email: str, company_name: str | None, pdf_url: str | None) -> tuple[str, str]:
    subject = f"Contractor induction approved \u2014 {(employee_name or 'Subcontractor')[:120]}"
    subject = subject  # subject rendered as plain text by the mail client
    pdf_html = ""
    href = _safe_href(pdf_url)
    if href:
        pdf_html = f'<p style="margin:14px 0 0;"><a href="{href}" style="background:{BRAND};color:#fff;text-decoration:none;font-weight:600;padding:10px 18px;border-radius:10px;display:inline-block;font-size:13px;">Open induction PDF &rarr;</a></p>'
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:20px;line-height:1.25;">Induction approved</h1>
      <p style="margin:0 0 6px;color:{MUTED};font-size:14px;line-height:1.55;">
        The following subcontractor has completed their PNC UNIQUE LTD induction and has been approved by HR. They are cleared to begin work.
      </p>
      {_employee_block(employee_name, employee_email, company_name)}
      {pdf_html}
    """
    return subject, _shell(preheader="A subcontractor under your supervision has been approved.", body_html=body)


def manager_rejection(employee_name: str, employee_email: str, company_name: str | None, note: str | None) -> tuple[str, str]:
    subject = f"Contractor induction rejected \u2014 {(employee_name or 'Subcontractor')[:120]}"
    note_html = ""
    if note:
        note_html = f"""
        <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin:14px 0 6px;">Rejection reason</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;">
          <tr><td style="padding:14px 18px;color:{INK};font-size:14px;line-height:1.55;white-space:pre-wrap;">{_e(note)}</td></tr>
        </table>
        """
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:20px;line-height:1.25;">Induction rejected</h1>
      <p style="margin:0 0 6px;color:{MUTED};font-size:14px;line-height:1.55;">
        The following subcontractor&#39;s induction has been rejected by PNC UNIQUE LTD HR. A new one-time access code has been sent to them so they can resubmit.
      </p>
      {_employee_block(employee_name, employee_email, company_name)}
      {note_html}
    """
    return subject, _shell(preheader="A subcontractor under your supervision has been rejected.", body_html=body)


def approval(full_name: str) -> tuple[str, str]:
    subject = "PNC Induction Approved"
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Welcome aboard, {_e(full_name) or 'there'}.</h1>
      <p style="margin:0 0 14px;color:{MUTED};font-size:14px;line-height:1.55;">
        Your induction has been reviewed and approved by PNC UNIQUE LTD HR. You are cleared to begin work \u2014 keep an eye on your email for project details from your site manager.
      </p>
      <p style="margin:0;color:{MUTED};font-size:12px;">
        If anything in your records needs updating later, contact PNC UNIQUE LTD HR.
      </p>
    """
    return subject, _shell(preheader="You&#39;re cleared to start work with PNC UNIQUE LTD.", body_html=body)


def rejection(
    full_name: str,
    note: str | None,
    *,
    portal_url: str | None = None,
    email: str | None = None,
    new_code: str | None = None,
) -> tuple[str, str]:
    subject = "Additional information required for your PNC induction"
    note_html = ""
    if note:
        note_html = f"""
        <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin:14px 0 6px;">From PNC UNIQUE LTD HR</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;">
          <tr><td style="padding:14px 18px;color:{INK};font-size:14px;line-height:1.55;white-space:pre-wrap;">{_e(note)}</td></tr>
        </table>
        """

    resubmit_html = ""
    href = _safe_href(portal_url)
    if new_code and href:
        resubmit_html = f"""
        <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin:22px 0 6px;">Resubmit your induction</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;margin-bottom:14px;">
          <tr><td style="padding:18px 20px;">
            <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;">Email address</div>
            <div style="font-weight:600;color:{INK};font-size:15px;margin-top:2px;">{_e(email)}</div>
            <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin-top:12px;">New access code</div>
            <div style="font-weight:700;font-family:'SFMono-Regular',Menlo,Consolas,monospace;color:{INK};font-size:18px;margin-top:2px;">{_e(new_code)}</div>
          </td></tr>
        </table>
        <p style="margin:0 0 14px;color:{INK};font-size:14px;line-height:1.55;">
          <b>Please complete the induction form again using the new access code.</b>
        </p>
        <p style="margin:0;">
          <a href="{href}" style="background:{BRAND};color:#FFFFFF;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:10px;display:inline-block;font-size:14px;">Restart my induction &rarr;</a>
        </p>
        <p style="margin:14px 0 0;color:{MUTED};font-size:12px;">
          Direct link: <a href="{href}" style="color:{BRAND};">{_e(portal_url)}</a>
        </p>
        """

    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Hi {_e(full_name) or 'there'},</h1>
      <p style="margin:0 0 14px;color:{MUTED};font-size:14px;line-height:1.55;">
        Thanks for completing your PNC UNIQUE LTD induction. After reviewing your submission, HR needs additional information before we can approve it.
      </p>
      {note_html}
      {resubmit_html}
      <p style="margin:18px 0 0;color:{MUTED};font-size:12px;line-height:1.55;">
        If you have any questions, just reply to this email or contact PNC UNIQUE LTD HR.
      </p>
    """
    return subject, _shell(preheader="PNC UNIQUE LTD HR needs more information for your induction.", body_html=body)
