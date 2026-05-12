# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/tasks/check_expiry.py
#
# Celery beat task: daily license expiry checker (runs at 09:00 UTC).
#
# What it does:
#   1. Loads all UserLicense records with status="active"
#   2. For each license:
#      a. If expires_at <= now → mark status="expired", save
#      b. If days_left <= 1 and alert_sent_1d=False → send alert, set flag
#      c. If days_left <= 7 and alert_sent_7d=False → send alert, set flag
#   3. Alerts go to SMTP email + Slack (if configured in .env.control)
#
# The alert_sent_* flags ensure each alert fires exactly once per license
# period.  They are reset to False when a license is renewed.
#
# Async inside Celery:
#   The Celery worker is synchronous, so check_expiry() wraps the async
#   _check() coroutine with asyncio.run().
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import AsyncSessionLocal
from models import Site, UserLicense
from services.email_alerts import alert_license_expiry
from tasks.celery_app import celery


async def _check():
    now = datetime.now(timezone.utc)
    thresholds = [1, 7]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserLicense).where(UserLicense.status == "active"))
        licenses = result.scalars().all()

        for lic in licenses:
            expires = lic.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)

            if expires <= now:
                lic.status = "expired"
                await db.commit()
                continue

            days_left = (expires - now).days

            site_result = await db.execute(select(Site).where(Site.id == lic.site_id))
            site = site_result.scalar_one_or_none()
            domain = site.domain if site else "unknown"

            if days_left <= 1 and not lic.alert_sent_1d:
                await alert_license_expiry(lic.user_email, domain, days_left)
                lic.alert_sent_1d = True
                await db.commit()
            elif days_left <= 7 and not lic.alert_sent_7d:
                await alert_license_expiry(lic.user_email, domain, days_left)
                lic.alert_sent_7d = True
                await db.commit()


@celery.task(name="tasks.check_expiry.check_expiry")
def check_expiry():
    asyncio.run(_check())
