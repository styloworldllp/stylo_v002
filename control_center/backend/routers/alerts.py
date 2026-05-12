# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/alerts.py
#
# Alert history log and manual test-send endpoint.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET  /api/alerts       — list alert events (placeholder; Sprint 4 adds DB)
#   POST /api/alerts/test  — send a test email/Slack message to verify config
#
# Automated alerts (license expiry at 7d and 1d) are fired by the Celery beat
# task in tasks/check_expiry.py — not by these endpoints.
#
# Test flow:
#   POST /api/alerts/test {"email": "me@example.com"}
#   → calls services/email_alerts.send_email() directly
#   → returns {"ok": true, "sent_to": "me@example.com"} or {"ok": false, ...}
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class TestAlertRequest(BaseModel):
    email: str = ""
    message: str = "Test alert from Stylo Control Center"


@router.get("")
async def list_alerts(_=Depends(get_current_user)):
    # Alert history will be stored in DB in Sprint 4 when Celery tasks are added
    return {"alerts": []}


@router.post("/test")
async def send_test_alert(body: TestAlertRequest, _=Depends(get_current_user)):
    from config import settings
    from services.email_alerts import send_email

    target = body.email or settings.smtp_user
    if not target:
        return {"ok": False, "detail": "No target email configured"}

    try:
        await send_email(
            to=target,
            subject="Stylo Control Center — Test Alert",
            body=body.message,
        )
        return {"ok": True, "sent_to": target}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
