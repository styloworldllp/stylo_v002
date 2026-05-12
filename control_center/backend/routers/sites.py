# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/sites.py
#
# CRUD endpoints for client site records.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET  /api/sites         — list all sites with active license count
#   POST /api/sites         — create a site record (does NOT provision containers)
#                             returns site_api_key — copy to client .env
#   GET  /api/sites/{id}    — full detail: licenses + last 20 deploy logs
#   PUT  /api/sites/{id}    — update domain, server assignment, image tag, notes
#   GET  /api/sites/{id}/logs — paginated deploy log list (default limit 50)
#
# Note: POST creates a DB record only. To actually start containers on the
# server, the admin must then call POST /api/deploy/provision/{site_id}.
# ─────────────────────────────────────────────────────────────────────────────
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import DeployLog, Site, UserLicense

router = APIRouter(prefix="/api/sites", tags=["sites"])


class SiteCreate(BaseModel):
    domain: str
    client_id: int
    server_id: int
    docker_image_tag: str = "latest"
    notes: str = ""


class SiteUpdate(BaseModel):
    domain: Optional[str] = None
    server_id: Optional[int] = None
    docker_image_tag: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def list_sites(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Site))
    sites = result.scalars().all()

    out = []
    for s in sites:
        lic_result = await db.execute(
            select(UserLicense).where(UserLicense.site_id == s.id, UserLicense.status == "active")
        )
        license_count = len(lic_result.scalars().all())
        out.append({
            "id": s.id,
            "domain": s.domain,
            "client_id": s.client_id,
            "server_id": s.server_id,
            "status": s.status,
            "docker_image_tag": s.docker_image_tag,
            "created_at": s.created_at,
            "last_deployed_at": s.last_deployed_at,
            "active_license_count": license_count,
        })
    return out


@router.post("", status_code=201)
async def create_site(body: SiteCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    site = Site(**body.model_dump())
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return {"id": site.id, "domain": site.domain, "site_api_key": site.site_api_key}


@router.get("/{site_id}")
async def get_site(site_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    licenses = await db.execute(select(UserLicense).where(UserLicense.site_id == site_id))
    logs = await db.execute(
        select(DeployLog).where(DeployLog.site_id == site_id).order_by(DeployLog.started_at.desc()).limit(20)
    )

    return {
        "id": site.id,
        "domain": site.domain,
        "client_id": site.client_id,
        "server_id": site.server_id,
        "status": site.status,
        "docker_image_tag": site.docker_image_tag,
        "site_api_key": site.site_api_key,
        "notes": site.notes,
        "created_at": site.created_at,
        "last_deployed_at": site.last_deployed_at,
        "licenses": [
            {
                "id": l.id,
                "user_email": l.user_email,
                "status": l.status,
                "issued_at": l.issued_at,
                "expires_at": l.expires_at,
                "revoked_at": l.revoked_at,
            }
            for l in licenses.scalars().all()
        ],
        "recent_logs": [
            {
                "id": log.id,
                "action": log.action,
                "image_tag": log.image_tag,
                "status": log.status,
                "started_at": log.started_at,
                "finished_at": log.finished_at,
            }
            for log in logs.scalars().all()
        ],
    }


@router.put("/{site_id}")
async def update_site(site_id: int, body: SiteUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(site, field, value)

    await db.commit()
    return {"ok": True}


@router.get("/{site_id}/logs")
async def site_logs(site_id: int, limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Site).where(Site.id == site_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site not found")

    logs = await db.execute(
        select(DeployLog).where(DeployLog.site_id == site_id).order_by(DeployLog.started_at.desc()).limit(limit)
    )
    return [
        {
            "id": l.id,
            "action": l.action,
            "image_tag": l.image_tag,
            "status": l.status,
            "log_output": l.log_output,
            "started_at": l.started_at,
            "finished_at": l.finished_at,
        }
        for l in logs.scalars().all()
    ]
