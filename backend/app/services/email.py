import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger("maf.email")

RESEND_ENDPOINT = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    html: str


def send(email: Email) -> bool:
    """
    Never raises. A send that fails must not fail the request behind it, and must not tell the
    caller whether an address exists. Failures go to the log (and to Sentry once a DSN is set).
    """
    if not settings.resend_api_key:
        # No key configured: the link goes to the console so development works offline.
        logger.info(
            "Email not sent (no RESEND_API_KEY)\n  to: %s\n  %s\n%s", email.to, email.subject, email.html
        )
        return False

    try:
        response = httpx.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from,
                "to": [email.to],
                "subject": email.subject,
                "html": email.html,
            },
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        logger.exception("Could not reach the email provider (to: %s)", email.to)
        return False

    if response.is_error:
        logger.error("Email rejected for %s: %s %s", email.to, response.status_code, response.text)
        return False
    return True


def _layout(heading: str, body: str, button_label: str, url: str, footer: str) -> str:
    return f"""\
<div style="font-family:-apple-system,'Segoe UI',sans-serif;background:#F6F3EC;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#FFF;border:1px solid #E2DDD1;
              border-radius:16px;padding:28px">
    <p style="margin:0 0 20px;font-size:20px;font-weight:700;color:#0E6B5C">MAF</p>
    <h1 style="margin:0 0 12px;font-size:22px;color:#1C1F1D">{heading}</h1>
    <p style="margin:0 0 22px;font-size:15px;line-height:1.55;color:#5B615C">{body}</p>
    <a href="{url}" style="display:inline-block;background:#0E6B5C;color:#FFF;text-decoration:none;
       padding:13px 22px;border-radius:12px;font-weight:600;font-size:15px">{button_label}</a>
    <p style="margin:22px 0 0;font-size:13px;line-height:1.5;color:#5B615C">{footer}</p>
    <p style="margin:12px 0 0;font-size:12px;color:#5B615C;word-break:break-all">{url}</p>
  </div>
</div>"""


def reset_email(to: str, full_name: str, url: str, hours: int) -> Email:
    return Email(
        to=to,
        subject="Reset your MAF password",
        html=_layout(
            heading=f"Hi {full_name}",
            body="Someone asked to reset the password on your MAF account. "
            "Choose a new one using the button below.",
            button_label="Set a new password",
            url=url,
            footer=f"This link works once and expires in {hours} hour{'s' if hours != 1 else ''}. "
            "If you didn't ask for it, you can ignore this email — your password stays as it is.",
        ),
    )


def invite_email(to: str, full_name: str, business_name: str, invited_by: str, url: str, days: int) -> Email:
    return Email(
        to=to,
        subject=f"{invited_by} added you to {business_name} on MAF",
        html=_layout(
            heading=f"Hi {full_name}",
            body=f"{invited_by} has added you to {business_name}. MAF is how you'll clock in and "
            "out of your shifts and see the hours you've worked.",
            button_label="Set up your account",
            url=url,
            footer=f"This invite expires in {days} days. Open it on the phone you'll use at work.",
        ),
    )
