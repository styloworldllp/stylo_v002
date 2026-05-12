# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/models/client.py
#
# SQLAlchemy model for a Styloworld client (the customer/organisation that
# purchased one or more site deployments).
#
# A Client is a billing/contact record — it is the parent of one or more Sites.
# Licenses are issued per-user per-site, not per-client.
#
# Fields:
#   name     — person or org name shown in the UI
#   email    — billing contact email; unique across all clients
#   company  — optional company name for display
#   phone    — optional contact phone number
#
# Relationships:
#   sites → list[Site] belonging to this client
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    sites: Mapped[list["Site"]] = relationship("Site", back_populates="client")  # noqa: F821
