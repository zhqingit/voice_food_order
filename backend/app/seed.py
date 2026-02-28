"""Seed the database with a test store for development."""

from __future__ import annotations

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.store import Store

TEST_STORE_EMAIL = "test@example.com"


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Store).filter(Store.email == TEST_STORE_EMAIL).first()
        if existing:
            print(f"Seed: store '{existing.name}' ({TEST_STORE_EMAIL}) already exists, skipping.")
            return

        store = Store(
            name="Test Kitchen",
            email=TEST_STORE_EMAIL,
            password_hash=hash_password("testpass123"),
            phone="+1-555-0100",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            postal_code="94102",
            country="US",
            allow_pickup=True,
            allow_delivery=True,
        )
        db.add(store)
        db.commit()
        print(f"Seeded test store '{store.name}' ({TEST_STORE_EMAIL}).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
