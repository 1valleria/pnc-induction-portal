"""HTML email templates for PNC HR notifications.

Plain inline-CSS, tables-based — kept simple so they render cleanly in Outlook,
Gmail and Apple Mail. No external CSS, no images.
"""
from __future__ import annotations

BRAND = "#166534"
INK = "#1C1917"
MUTED = "#57534E"
SOFT = "#FAFAF9"
LINE = "#E7E5E4"


def _shell(*, preheader: str, body_html: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PNC Induction</title>
</head>
<body style="margin:0;padding:0;background:{SOFT};font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{INK};">
  <span style="display:none;visibility:hidden;opacity:0;color:transparent;height:0;width:0;">{preheader}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;border:1px solid {LINE};border-radius:14px;overflow:hidden;">
        <tr><td style="background:{BRAND};padding:20px 28px;">
          <div style="color:#BBF7D0;font-size:11px;letter-spacing:.18em;font-weight:700;">PNC INDUCTION PORTAL</div>
        </td></tr>
        <tr><td style="padding:28px;">
          {body_html}
          <p style="margin:28px 0 0;color:{MUTED};font-size:12px;line-height:1.5;">
            If you weren't expecting this email, please ignore it or contact PNC HR.
          </p>
        </td></tr>
      </table>
      <div style="color:{MUTED};font-size:11px;margin-top:16px;">© PNC · confidential</div>
    </td></tr>
  </table>
</body>
</html>"""


def invitation(full_name: str, portal_url: str, email: str, code: str) -> tuple[str, str]:
    subject = "Your PNC induction — action required"
    preheader = "Complete your digital induction in 5 minutes."
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Hi {full_name or 'there'},</h1>
      <p style="margin:0 0 18px;color:{MUTED};font-size:14px;line-height:1.55;">
        You've been invited to complete your PNC subcontractor induction. The form takes about 5 minutes on a phone and only needs to be done once.
      </p>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;margin:14px 0;">
        <tr><td style="padding:18px 20px;">
          <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;">Email address</div>
          <div style="font-weight:600;color:{INK};font-size:15px;margin-top:2px;">{email}</div>
          <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin-top:12px;">Access code</div>
          <div style="font-weight:700;font-family:'SFMono-Regular',Menlo,Consolas,monospace;color:{INK};font-size:18px;margin-top:2px;">{code}</div>
        </td></tr>
      </table>

      <p style="margin:18px 0 8px;">
        <a href="{portal_url}" style="background:{BRAND};color:#FFFFFF;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:10px;display:inline-block;font-size:14px;">Start my induction →</a>
      </p>
      <p style="margin:14px 0 0;color:{MUTED};font-size:12px;">
        Direct link: <a href="{portal_url}" style="color:{BRAND};">{portal_url}</a>
      </p>
    """
    return subject, _shell(preheader=preheader, body_html=body)


def approval(full_name: str) -> tuple[str, str]:
    subject = "PNC Induction Approved"
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Welcome aboard, {full_name or 'there'}.</h1>
      <p style="margin:0 0 14px;color:{MUTED};font-size:14px;line-height:1.55;">
        Your induction has been reviewed and approved by PNC HR. You are cleared to begin work — keep an eye on your email for project details from your site manager.
      </p>
      <p style="margin:0;color:{MUTED};font-size:12px;">
        If anything in your records needs updating later, contact PNC HR.
      </p>
    """
    return subject, _shell(preheader="You're cleared to start work with PNC.", body_html=body)


def rejection(full_name: str, note: str | None) -> tuple[str, str]:
    subject = "Additional information required for your PNC induction"
    note_html = ""
    if note:
        note_html = f"""
        <div style="font-size:11px;letter-spacing:.18em;color:{MUTED};font-weight:600;text-transform:uppercase;margin:14px 0 6px;">From PNC HR</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SOFT};border:1px solid {LINE};border-radius:12px;">
          <tr><td style="padding:14px 18px;color:{INK};font-size:14px;line-height:1.55;white-space:pre-wrap;">{note}</td></tr>
        </table>
        """
    body = f"""
      <h1 style="margin:0 0 6px;color:{INK};font-size:22px;line-height:1.25;">Hi {full_name or 'there'},</h1>
      <p style="margin:0 0 14px;color:{MUTED};font-size:14px;line-height:1.55;">
        Thanks for completing your PNC induction. After reviewing your submission, PNC HR needs additional information before we can approve it.
      </p>
      {note_html}
      <p style="margin:18px 0 0;color:{MUTED};font-size:13px;line-height:1.55;">
        Please reply to this email or contact PNC HR to provide the information requested above. Once we have it, you can resubmit your induction or we'll update your record directly.
      </p>
    """
    return subject, _shell(preheader="PNC HR needs more information for your induction.", body_html=body)
