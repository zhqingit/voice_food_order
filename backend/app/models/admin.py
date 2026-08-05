from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class Admin(Base):
    """Platform operator. Reviews stores, sets commission, suspends accounts.

    Third auth role alongside User (mobile) and Store (web); no self-signup —
    admins are provisioned out of band.
    """

    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Store naive UTC timestamps for cross-DB compatibility (sqlite tests + Postgres prod)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
