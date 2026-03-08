from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import ForeignKey, Integer, SmallInteger, Time, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StoreHours(Base):
    __tablename__ = "store_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon .. 6=Sun
    open_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(9, 0))
    close_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(21, 0))
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
