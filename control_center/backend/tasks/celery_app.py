# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/tasks/celery_app.py
#
# Celery application configuration and beat schedule.
#
# The worker + beat process is started in docker-compose.control.yml:
#   celery -A tasks.celery_app worker --beat --loglevel=info
#
# Beat schedule:
#   check-license-expiry  — runs daily at 09:00 UTC
#     → tasks/check_expiry.py: marks expired licenses, sends 7d and 1d alerts
#
#   health-check-sites    — runs every 5 minutes (300s)
#     → tasks/health_check.py: SSHes into each server to check container state
#
# Both tasks use asyncio.run() to execute async SQLAlchemy + SSH calls inside
# the synchronous Celery worker context.
# ─────────────────────────────────────────────────────────────────────────────
from celery import Celery
from celery.schedules import crontab

from config import settings

celery = Celery("stylo_control", broker=settings.redis_url, backend=settings.redis_url)

celery.conf.beat_schedule = {
    "check-license-expiry": {
        "task": "tasks.check_expiry.check_expiry",
        "schedule": crontab(hour=9, minute=0),  # daily at 9am
    },
    "health-check-sites": {
        "task": "tasks.health_check.health_check_all",
        "schedule": 300.0,  # every 5 minutes
    },
}

celery.conf.timezone = "UTC"
