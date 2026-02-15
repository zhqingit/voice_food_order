from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from app.core.time import utcnow_naive


@dataclass
class TokenBucket:
    capacity: int
    refill_per_second: float
    tokens: float | None = None
    last_refill: float | None = None

    def __post_init__(self) -> None:
        if self.tokens is None:
            self.tokens = float(self.capacity)
        if self.last_refill is None:
            self.last_refill = time.monotonic()

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - (self.last_refill or now)
        refill = elapsed * self.refill_per_second
        self.tokens = min(self.capacity, (self.tokens or 0.0) + refill)
        self.last_refill = now
        if (self.tokens or 0.0) < cost:
            return False
        self.tokens = (self.tokens or 0.0) - cost
        return True


def ensure_max_duration(*, started_at: datetime, max_seconds: int) -> bool:
    return (utcnow_naive() - started_at).total_seconds() <= max_seconds
