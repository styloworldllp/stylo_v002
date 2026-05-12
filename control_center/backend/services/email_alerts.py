# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/services/email_alerts.py
#
# Outbound alert delivery — email (SMTP) and Slack webhook.
#
# Functions:
#   send_email(to, subject, body)
#     Sends a plain-text email via SMTP STARTTLS.  Runs in a thread executor
#     since smtplib is synchronous.  Credentials come from settings (smtp_*).
#
#   send_slack(message)
#     Posts a Slack message via incoming webhook URL (settings.slack_webhook_url).
#     No-ops silently if the webhook URL is not configured.
#
#   alert_license_expiry(user_email, site_domain, days_left)
#     High-level helper called by tasks/check_expiry.py.
#     Sends both email and Slack in parallel (asyncio.gather).
#     Only fires if the respective service is configured in .env.control.
#
# Called by:
#   tasks/check_expiry.py — daily Celery task checking for 7d + 1d expiries
#   routers/alerts.py     — POST /api/alerts/test for manual verification
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import smtplib
from email.mime.text import MIMEText

import httpx

from config import settings


async def send_email(to: str, subject: str, body: str) -> None:
    def _send():
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.alert_from_email
        msg["To"] = to

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

    await asyncio.get_event_loop().run_in_executor(None, _send)


async def send_slack(message: str) -> None:
    if not settings.slack_webhook_url:
        return
    async with httpx.AsyncClient() as client:
        await client.post(settings.slack_webhook_url, json={"text": message})


async def alert_license_expiry(user_email: str, site_domain: str, days_left: int) -> None:
    subject = f"License expiring in {days_left} day(s) — {site_domain}"
    body = (
        f"The license for {user_email} on {site_domain} will expire in {days_left} day(s).\n\n"
        f"Log in to Stylo Control Center to renew."
    )
    slack_msg = f":warning: License expiring in {days_left}d: *{user_email}* on `{site_domain}`"

    tasks = []
    if settings.smtp_host:
        tasks.append(send_email(settings.smtp_user, subject, body))
    if settings.slack_webhook_url:
        tasks.append(send_slack(slack_msg))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
