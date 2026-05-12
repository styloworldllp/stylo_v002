# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/lbalancer.py
#
# Traefik load balancer config generation and push.
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET  /api/lbalancer/preview     — show what the YAML would look like
#                                     without writing anything to disk
#   POST /api/lbalancer/regenerate  — rebuild sites.yml from all active sites
#                                     and push it to the Traefik server via SFTP
#
# Config format (Traefik file provider):
#   http:
#     routers:
#       acme-site:
#         rule: 'Host(`acme.styloworld.io`)'
#         service: acme-site
#         entryPoints: [websecure]
#         tls: { certResolver: letsencrypt }
#     services:
#       acme-site:
#         loadBalancer:
#           servers:
#             - url: "http://<server-hostname>:8000"
#
# Traefik watches the file via its file provider and auto-reloads when it
# changes — no restart needed.
#
# Config for the Traefik SSH connection is read from settings (traefik_*).
# ─────────────────────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Server, Site

router = APIRouter(prefix="/api/lbalancer", tags=["lbalancer"])


def _build_traefik_config(sites_with_servers: list[tuple[Site, Server]]) -> str:
    routers = {}
    services = {}

    for site, server in sites_with_servers:
        key = site.domain.replace(".", "-").replace("_", "-")
        routers[key] = {
            "rule": f'Host(`{site.domain}`)',
            "service": key,
            "entryPoints": ["websecure"],
            "tls": {"certResolver": "letsencrypt"},
        }
        services[key] = {
            "loadBalancer": {
                "servers": [{"url": f"http://{server.hostname}:8000"}]
            }
        }

    import yaml
    config = {"http": {"routers": routers, "services": services}}
    return yaml.dump(config, default_flow_style=False)


@router.get("/preview")
async def preview_config(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Site).where(Site.status == "active"))
    sites = result.scalars().all()

    pairs = []
    for site in sites:
        srv = await db.execute(select(Server).where(Server.id == site.server_id))
        server = srv.scalar_one_or_none()
        if server:
            pairs.append((site, server))

    return {"config": _build_traefik_config(pairs)}


@router.post("/regenerate")
async def regenerate(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings
    from services.ssh import ssh_write_file

    result = await db.execute(select(Site).where(Site.status == "active"))
    sites = result.scalars().all()

    pairs = []
    for site in sites:
        srv = await db.execute(select(Server).where(Server.id == site.server_id))
        server = srv.scalar_one_or_none()
        if server:
            pairs.append((site, server))

    config_yaml = _build_traefik_config(pairs)

    traefik_server = Server(
        hostname=settings.traefik_server_host,
        ssh_port=22,
        ssh_user=settings.traefik_ssh_user,
        ssh_private_key=open(settings.traefik_ssh_key_path).read(),
    )

    await ssh_write_file(traefik_server, settings.traefik_config_path, config_yaml)

    return {"ok": True, "sites_configured": len(pairs)}
