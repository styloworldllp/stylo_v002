# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/models/server.py
#
# SQLAlchemy model for a managed client server (physical/cloud VPS).
#
# A Server is a machine the Control Center can SSH into to run Docker commands.
# One server can host multiple Site containers.
#
# Fields:
#   name            — human-readable label shown in the UI (e.g. "EU-West-1")
#   hostname        — IP address or FQDN used for SSH connections
#   ssh_port/user   — SSH connection parameters (defaults: 22 / root)
#   ssh_private_key — full PEM private key content stored in DB;
#                     used by services/ssh.py to authenticate
#   region          — optional region tag for display/grouping only
#   max_sites       — soft cap; the UI warns when site_count approaches this
#   is_active       — soft-disable the server without deleting the record
#
# Relationships:
#   sites → list[Site] deployed on this server
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    hostname: Mapped[str] = mapped_column(String(255))
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[str] = mapped_column(String(100), default="root")
    ssh_private_key: Mapped[str] = mapped_column(String(4096))  # PEM key content
    region: Mapped[str] = mapped_column(String(50), default="")
    max_sites: Mapped[int] = mapped_column(Integer, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    sites: Mapped[list["Site"]] = relationship("Site", back_populates="server")  # noqa: F821
