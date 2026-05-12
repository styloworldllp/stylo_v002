# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/sync.py
#
# Machine-to-machine sync endpoint — called by stylo_core Frappe benches,
# NOT by human admin users.  No JWT required; authenticated by site API key.
#
# Endpoint:
#   GET /api/sync/{site_domain}/users
#     Headers: X-Site-Api-Key: <site.site_api_key>
#     Returns: {"licensed": ["user@a.com", ...], "revoked": ["user@b.com", ...]}
#
# Authentication:
#   _verify_site_key() looks up the site by domain and compares the key in the
#   header against site.site_api_key stored in the DB (constant-time string
#   comparison is fine here since the key is a 64-char hex secret).
#
# License resolution:
#   A license is "licensed" when status="active" AND expires_at > now.
#   Everything else (revoked, expired, or future status) goes into "revoked".
#   The bench caches this list for 15 minutes and checks it on every login.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Site, UserLicense

router = APIRouter(prefix="/api/sync", tags=["sync"])


async def _verify_site_key(domain: str, x_site_api_key: str, db: AsyncSession) -> Site:
    result = await db.execute(select(Site).where(Site.domain == domain))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if site.site_api_key != x_site_api_key:
        raise HTTPException(status_code=401, detail="Invalid site API key")
    return site


@router.get("/{site_domain}/users")
async def sync_users(
    site_domain: str,
    x_site_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Called by stylo_core bench every 5 minutes to get per-user module licenses."""
    site = await _verify_site_key(site_domain, x_site_api_key, db)

    now = datetime.now(timezone.utc)

    result = await db.execute(select(UserLicense).where(UserLicense.site_id == site.id))
    all_licenses = result.scalars().all()

    users: dict[str, list[str]] = {}

    for lic in all_licenses:
        expires = lic.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if lic.status == "active" and expires > now:
            users[lic.user_email] = lic.modules or []

    return {"users": users}
