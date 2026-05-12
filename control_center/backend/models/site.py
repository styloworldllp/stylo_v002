# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/models/site.py
#
# Two SQLAlchemy models: Site and DeployLog.
#
# ── Site ──────────────────────────────────────────────────────────────────────
# A Site is one Frappe bench deployment running on a Server.
#
# Lifecycle:  provisioning → active → suspended ↔ active → terminated
#
# Fields:
#   domain          — public FQDN routed by Traefik (e.g. "acme.styloworld.io")
#   client_id       — owning client
#   server_id       — host server for Docker containers
#   status          — current lifecycle state
#   docker_image_tag — tag used for docker pull / docker compose (e.g. "latest")
#   site_api_key    — 64-hex secret auto-generated at record creation;
#                     stored in client .env as STYLO_SITE_API_KEY and sent in
#                     the X-Site-Api-Key header to authenticate sync requests
#   last_deployed_at — updated on successful provision/deploy
#
# ── DeployLog ─────────────────────────────────────────────────────────────────
# Append-only record of every SSH deploy operation.
# Created immediately when the action is dispatched (status=running); updated
# to success/failed by the async background task in routers/deploy.py.
#
# Fields:
#   action      — provision | deploy | suspend | resume | terminate
#   status      — running | success | failed
#   log_output  — stdout/stderr captured from SSH commands
#   started_at  — task dispatch time
#   finished_at — completion time (null while running)
# ─────────────────────────────────────────────────────────────────────────────
import secrets
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    # provisioning | active | suspended | terminated
    status: Mapped[str] = mapped_column(String(30), default="provisioning")
    docker_image_tag: Mapped[str] = mapped_column(String(100), default="latest")
    # Secret used by stylo_core bench to authenticate sync requests
    site_api_key: Mapped[str] = mapped_column(
        String(64), default=lambda: secrets.token_hex(32)
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped["Client"] = relationship("Client", back_populates="sites")  # noqa: F821
    server: Mapped["Server"] = relationship("Server", back_populates="sites")  # noqa: F821
    licenses: Mapped[list["UserLicense"]] = relationship("UserLicense", back_populates="site")  # noqa: F821
    deploy_logs: Mapped[list["DeployLog"]] = relationship("DeployLog", back_populates="site")  # noqa: F821


class DeployLog(Base):
    __tablename__ = "deploy_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    action: Mapped[str] = mapped_column(String(30))  # provision|deploy|suspend|resume|terminate
    image_tag: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|success|failed
    log_output: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    site: Mapped[Site] = relationship("Site", back_populates="deploy_logs")
