from __future__ import annotations

from pydantic import BaseModel, field_validator


class DayHours(BaseModel):
    day_of_week: int  # 0=Mon .. 6=Sun
    open_time: str  # "HH:MM"
    close_time: str  # "HH:MM"
    is_closed: bool = False

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError("day_of_week must be 0-6")
        return v

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be HH:MM")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time")
        return f"{h:02d}:{m:02d}"


class StoreHoursUpdate(BaseModel):
    hours: list[DayHours]
