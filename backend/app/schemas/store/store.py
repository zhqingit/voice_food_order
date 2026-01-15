from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class StoreOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: EmailStr
    created_at: datetime
