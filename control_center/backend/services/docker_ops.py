# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/services/docker_ops.py
#
# High-level Docker operations executed via SSH on a client server.
# Each function maps to one deploy router action.
#
# Container layout on the server:
#   /opt/stylo/sites/{safe_domain}/   — per-site working directory
#   /opt/stylo/docker-compose.client.yml — shared compose template
#
# The safe_domain is the FQDN with dots/dashes replaced by underscores to
# produce a valid directory name and Docker service name prefix.
#
# Compose env vars injected at runtime (via shell prefixes):
#   SITE_DOMAIN         — used inside the container as SITE_NAME
#   IMAGE_TAG           — which Docker image tag to pull
#   STYLO_SITE_API_KEY  — stored in the container env for Control Center sync
#
# Functions:
#   provision_site  — docker pull + docker compose up -d (new install)
#   update_site     — docker pull + rolling restart of web + worker only
#   suspend_site    — docker compose stop web worker socketio
#   resume_site     — docker compose start web worker socketio
#   terminate_site  — docker compose down -v + rm -rf site directory
# ─────────────────────────────────────────────────────────────────────────────
"""SSH-based Docker operations for client site containers."""
from models import Server, Site
from services.ssh import ssh_run

COMPOSE_DIR = "/opt/stylo/sites"


def _site_dir(site: Site) -> str:
    safe_name = site.domain.replace(".", "_").replace("-", "_")
    return f"{COMPOSE_DIR}/{safe_name}"


def _compose_env(site: Site) -> str:
    return (
        f"SITE_DOMAIN={site.domain} "
        f"IMAGE_TAG={site.docker_image_tag} "
        f"STYLO_SITE_API_KEY={site.site_api_key}"
    )


async def provision_site(server: Server, site: Site) -> str:
    """Pull image and start all containers for a new site."""
    site_dir = _site_dir(site)
    env = _compose_env(site)

    commands = [
        f"mkdir -p {site_dir}",
        f"docker pull ghcr.io/styloworld/stylo-bench:{site.docker_image_tag}",
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml up -d",
    ]
    output = []
    for cmd in commands:
        out = await ssh_run(server, cmd)
        output.append(out)
    return "\n".join(output)


async def update_site(server: Server, site: Site) -> str:
    """Pull latest image and rolling restart."""
    site_dir = _site_dir(site)
    env = _compose_env(site)

    commands = [
        f"docker pull ghcr.io/styloworld/stylo-bench:{site.docker_image_tag}",
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml up -d --no-deps web",
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml up -d --no-deps worker",
    ]
    output = []
    for cmd in commands:
        out = await ssh_run(server, cmd)
        output.append(out)
    return "\n".join(output)


async def suspend_site(server: Server, site: Site) -> str:
    """Stop web and worker containers (keep DB/Redis up)."""
    site_dir = _site_dir(site)
    env = _compose_env(site)
    return await ssh_run(
        server,
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml stop web worker socketio",
    )


async def resume_site(server: Server, site: Site) -> str:
    """Restart web and worker containers."""
    site_dir = _site_dir(site)
    env = _compose_env(site)
    return await ssh_run(
        server,
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml start web worker socketio",
    )


async def terminate_site(server: Server, site: Site) -> str:
    """Tear down all containers and volumes."""
    site_dir = _site_dir(site)
    env = _compose_env(site)
    return await ssh_run(
        server,
        f"cd {site_dir} && {env} docker compose -f /opt/stylo/docker-compose.client.yml down -v && rm -rf {site_dir}",
    )
