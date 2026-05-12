# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/licenses.py
#
# User license management — issue, revoke, renew, and delete per-user licenses.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET  /api/licenses              — list licenses; filter by site_id or status
#   POST /api/licenses              — issue a new license for a user on a site
#                                     (rejects duplicates: active license exists)
#   PUT  /api/licenses/{id}/revoke  — immediately mark license as revoked;
#                                     bench will stop admitting the user within
#                                     5 minutes (next sync poll cycle)
#   PUT  /api/licenses/{id}/renew   — extend expiry date; resets alert flags so
#                                     expiry notifications fire again
#   DELETE /api/licenses/{id}       — hard-delete the record
#
# Revocation flow:
#   revoke sets status="revoked" + revoked_at=now
#   → next bench poll excludes this email from the licensed list
#   → user blocked on next login attempt (within 5 min)
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import UserLicense

router = APIRouter(prefix="/api/licenses", tags=["licenses"])


class LicenseCreate(BaseModel):
    site_id: int
    user_email: str
    expires_at: datetime
    # e.g. ["bms", "crm"] or ["pro"] for full access
    modules: list[str] = []


class LicenseRenew(BaseModel):
    expires_at: datetime


@router.get("")
async def list_licenses(
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(UserLicense)
    if site_id:
        query = query.where(UserLicense.site_id == site_id)
    if status:
        query = query.where(UserLicense.status == status)

    result = await db.execute(query.order_by(UserLicense.issued_at.desc()))
    licenses = result.scalars().all()

    return [
        {
            "id": l.id,
            "site_id": l.site_id,
            "user_email": l.user_email,
            "status": l.status,
            "modules": l.modules or [],
            "issued_at": l.issued_at,
            "expires_at": l.expires_at,
            "revoked_at": l.revoked_at,
        }
        for l in licenses
    ]


@router.post("", status_code=201)
async def issue_license(body: LicenseCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    existing = await db.execute(
        select(UserLicense).where(
            UserLicense.site_id == body.site_id,
            UserLicense.user_email == body.user_email,
            UserLicense.status == "active",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Active license already exists for this user on this site")

    license = UserLicense(**body.model_dump())
    db.add(license)
    await db.commit()
    await db.refresh(license)
    return {"id": license.id, "user_email": license.user_email, "status": license.status}


@router.put("/{license_id}/revoke")
async def revoke_license(license_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(UserLicense).where(UserLicense.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    if license.status == "revoked":
        raise HTTPException(status_code=400, detail="License already revoked")

    license.status = "revoked"
    license.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "revoked_at": license.revoked_at}


@router.put("/{license_id}/renew")
async def renew_license(license_id: int, body: LicenseRenew, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(UserLicense).where(UserLicense.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    license.expires_at = body.expires_at
    if license.status == "expired":
        license.status = "active"
    license.alert_sent_7d = False
    license.alert_sent_1d = False
    await db.commit()
    return {"ok": True, "expires_at": license.expires_at}


@router.delete("/{license_id}")
async def delete_license(license_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(UserLicense).where(UserLicense.id == license_id))
    license = result.scalar_one_or_none()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    await db.delete(license)
    await db.commit()
    return {"ok": True}
