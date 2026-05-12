# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/models/license.py
#
# SQLAlchemy model for a per-user site license.
#
# Key design decision:
#   Licenses are per USER EMAIL per SITE — not per domain.
#   A single client site can have many users; each user needs their own license.
#   The Control Center is the source of truth; stylo_core benches poll
#   GET /api/sync/{domain}/users every 5 minutes to refresh their local cache.
#
# Fields:
#   site_id       — foreign key to sites.id (the deployment this applies to)
#   user_email    — Frappe user email on the client bench; must match exactly
#   status        — active | revoked | expired
#   issued_at     — when the license was created
#   expires_at    — the hard expiry date; bench poll excludes expired licenses
#   revoked_at    — set when an admin explicitly revokes; takes effect within
#                   5 minutes (next bench poll cycle)
#   alert_sent_7d — tracks whether the 7-day expiry email has been sent
#   alert_sent_1d — tracks whether the 1-day expiry email has been sent
#                   (reset to False on renewal so alerts fire again)
#
# Relationships:
#   site → Site this license belongs to
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserLicense(Base):
    __tablename__ = "user_licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    user_email: Mapped[str] = mapped_column(String(255))
    # active | revoked | expired
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Module license keys: ["bms", "crm", "hr", "lms"] or ["pro"] for full access
    modules: Mapped[list] = mapped_column(JSON, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alert_sent_7d: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent_1d: Mapped[bool] = mapped_column(Boolean, default=False)

    site: Mapped["Site"] = relationship("Site", back_populates="licenses")  # noqa: F821
