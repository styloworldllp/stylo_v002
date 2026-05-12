# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/servers.py
#
# CRUD endpoints for managed servers + SSH health check.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET    /api/servers           — list all servers with live site_count
#   POST   /api/servers           — register a new server (stores PEM key in DB)
#   PUT    /api/servers/{id}      — update any server field (key is optional)
#   DELETE /api/servers/{id}      — remove server; blocked if active sites exist
#   GET    /api/servers/{id}/health — SSH in, run `docker ps`, return containers
#
# Notes:
#   • list_servers() makes one extra DB query per server to count sites —
#     acceptable for the expected scale of < 50 servers
#   • delete_server() checks for provisioning/active/suspended sites first to
#     prevent orphaning live containers
#   • server_health() delegates to services/ssh.py; returns {"status":"error"}
#     (not an HTTP error) so the UI can display the failure gracefully
# ─────────────────────────────────────────────────────────────────────────────
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Server, Site

router = APIRouter(prefix="/api/servers", tags=["servers"])


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_private_key: str
    region: str = ""
    max_sites: int = 20


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_private_key: Optional[str] = None
    region: Optional[str] = None
    max_sites: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_servers(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Server))
    servers = result.scalars().all()

    out = []
    for s in servers:
        count_result = await db.execute(
            select(func.count()).select_from(Site).where(Site.server_id == s.id, Site.status != "terminated")
        )
        site_count = count_result.scalar()
        out.append({
            "id": s.id,
            "name": s.name,
            "hostname": s.hostname,
            "ssh_port": s.ssh_port,
            "ssh_user": s.ssh_user,
            "region": s.region,
            "max_sites": s.max_sites,
            "is_active": s.is_active,
            "created_at": s.created_at,
            "site_count": site_count,
        })
    return out


@router.post("", status_code=201)
async def create_server(body: ServerCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    server = Server(**body.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return {"id": server.id, "name": server.name}


@router.put("/{server_id}")
async def update_server(server_id: int, body: ServerUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(server, field, value)

    await db.commit()
    return {"ok": True}


@router.delete("/{server_id}")
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    active = await db.execute(
        select(func.count()).select_from(Site).where(Site.server_id == server_id, Site.status.in_(["provisioning", "active", "suspended"]))
    )
    if active.scalar() > 0:
        raise HTTPException(status_code=400, detail="Cannot remove server with active sites")

    await db.delete(server)
    await db.commit()
    return {"ok": True}


@router.get("/{server_id}/health")
async def server_health(server_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from services.ssh import ssh_run

    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        output = await ssh_run(server, "docker ps --format '{{.Names}}'")
        return {"status": "ok", "containers": output.strip().splitlines()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
