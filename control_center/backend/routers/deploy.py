# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/deploy.py
#
# Async deployment operations — each endpoint fires an SSH action on the
# target server without blocking the HTTP response.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints (all return HTTP 202 Accepted + {"log_id": N, "status": "running"}):
#   POST /api/deploy/provision/{site_id} — docker pull + docker compose up -d
#   POST /api/deploy/update/{site_id}    — docker pull + rolling restart of
#                                          web + worker containers
#   POST /api/deploy/suspend/{site_id}   — docker compose stop (keeps DB/Redis)
#   POST /api/deploy/resume/{site_id}    — docker compose start
#   POST /api/deploy/terminate/{site_id} — docker compose down -v + rm site dir
#   GET  /api/deploy/logs/{log_id}       — poll log status + output
#
# Async pattern:
#   1. _run_deploy_action() creates a DeployLog row (status="running") and
#      immediately fires asyncio.create_task(_execute_action(...))
#   2. The HTTP response returns the log_id so the frontend can poll
#   3. _execute_action() opens its own DB session, runs the SSH command,
#      then updates DeployLog.status + Site.status on completion
#   4. Frontend's DeployLogModal polls GET /api/deploy/logs/{id} every 3s
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import DeployLog, Server, Site

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


async def _run_deploy_action(site_id: int, action: str, db: AsyncSession):
    """Create a DeployLog and run SSH operation in background."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    srv_result = await db.execute(select(Server).where(Server.id == site.server_id))
    server = srv_result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=500, detail="Server record missing")

    log = DeployLog(site_id=site_id, action=action, image_tag=site.docker_image_tag, status="running")
    db.add(log)
    await db.commit()
    await db.refresh(log)

    asyncio.create_task(_execute_action(log.id, site, server, action))
    return {"log_id": log.id, "status": "running"}


async def _execute_action(log_id: int, site: Site, server: Server, action: str):
    from database import AsyncSessionLocal
    from services.docker_ops import (
        provision_site,
        resume_site,
        suspend_site,
        terminate_site,
        update_site,
    )

    async with AsyncSessionLocal() as db:
        try:
            if action == "provision":
                output = await provision_site(server, site)
            elif action == "deploy":
                output = await update_site(server, site)
            elif action == "suspend":
                output = await suspend_site(server, site)
            elif action == "resume":
                output = await resume_site(server, site)
            elif action == "terminate":
                output = await terminate_site(server, site)
            else:
                output = f"Unknown action: {action}"

            result = await db.execute(select(DeployLog).where(DeployLog.id == log_id))
            log = result.scalar_one()
            log.status = "success"
            log.log_output = output
            log.finished_at = datetime.now(timezone.utc)

            if action == "provision":
                site_result = await db.execute(select(Site).where(Site.id == site.id))
                s = site_result.scalar_one()
                s.status = "active"
                s.last_deployed_at = datetime.now(timezone.utc)
            elif action == "deploy":
                site_result = await db.execute(select(Site).where(Site.id == site.id))
                s = site_result.scalar_one()
                s.last_deployed_at = datetime.now(timezone.utc)
            elif action == "suspend":
                site_result = await db.execute(select(Site).where(Site.id == site.id))
                s = site_result.scalar_one()
                s.status = "suspended"
            elif action == "resume":
                site_result = await db.execute(select(Site).where(Site.id == site.id))
                s = site_result.scalar_one()
                s.status = "active"
            elif action == "terminate":
                site_result = await db.execute(select(Site).where(Site.id == site.id))
                s = site_result.scalar_one()
                s.status = "terminated"

            await db.commit()

        except Exception as e:
            result = await db.execute(select(DeployLog).where(DeployLog.id == log_id))
            log = result.scalar_one()
            log.status = "failed"
            log.log_output = str(e)
            log.finished_at = datetime.now(timezone.utc)
            await db.commit()


@router.post("/provision/{site_id}", status_code=202)
async def provision(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _run_deploy_action(site_id, "provision", db)


@router.post("/update/{site_id}", status_code=202)
async def update(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _run_deploy_action(site_id, "deploy", db)


@router.post("/suspend/{site_id}", status_code=202)
async def suspend(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _run_deploy_action(site_id, "suspend", db)


@router.post("/resume/{site_id}", status_code=202)
async def resume(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _run_deploy_action(site_id, "resume", db)


@router.post("/terminate/{site_id}", status_code=202)
async def terminate(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _run_deploy_action(site_id, "terminate", db)


@router.get("/logs/{log_id}")
async def get_log(log_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(DeployLog).where(DeployLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return {
        "id": log.id,
        "site_id": log.site_id,
        "action": log.action,
        "image_tag": log.image_tag,
        "status": log.status,
        "log_output": log.log_output,
        "started_at": log.started_at,
        "finished_at": log.finished_at,
    }
