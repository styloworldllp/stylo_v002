# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/tasks/health_check.py
#
# Celery beat task: site health check (runs every 5 minutes).
#
# What it does:
#   1. Loads all Site records with status in [active, suspended]
#   2. For each site, SSHes into its Server and runs:
#        docker ps --filter name={safe_name} --format '{{.Status}}'
#   3. If the container shows "Up" → marks site status as "active"
#      (brings back a site that recovered from a transient blip)
#   4. SSH errors are silently ignored — a single failure doesn't flip status
#      (avoids false-positive suspensions on network hiccups)
#
# Note:
#   The check does NOT auto-suspend sites where containers are down —
#   that would cause false positives during intentional restarts.
#   Only admin-triggered actions change status to "suspended" / "terminated".
# ─────────────────────────────────────────────────────────────────────────────
import asyncio

from sqlalchemy import select

from database import AsyncSessionLocal
from models import Server, Site
from services.ssh import ssh_run
from tasks.celery_app import celery


async def _ping_site(site: Site, server: Server) -> str:
    try:
        safe_name = site.domain.replace(".", "_").replace("-", "_")
        out = await ssh_run(server, f"docker ps --filter name={safe_name} --format '{{{{.Status}}}}'")
        if "Up" in out:
            return "active"
        return "suspended"
    except Exception:
        return "error"


async def _run_health_checks():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Site).where(Site.status.in_(["active", "suspended"])))
        sites = result.scalars().all()

        for site in sites:
            srv_result = await db.execute(select(Server).where(Server.id == site.server_id))
            server = srv_result.scalar_one_or_none()
            if not server:
                continue

            status = await _ping_site(site, server)
            if status == "active" and site.status != "active":
                site.status = "active"
                await db.commit()
            elif status == "suspended" and site.status == "active":
                pass  # don't auto-downgrade, may be transient


@celery.task(name="tasks.health_check.health_check_all")
def health_check_all():
    asyncio.run(_run_health_checks())
