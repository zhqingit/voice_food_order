"""Provision a platform admin (no self-signup).

Usage:
    python -m app.cli.create_admin <email> <password>
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_db_session
from app.models.admin import Admin


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m app.cli.create_admin <email> <password>", file=sys.stderr)
        return 2

    email = argv[0].strip().lower()
    password = argv[1]
    if len(password) < 8:
        print("password must be at least 8 characters", file=sys.stderr)
        return 2

    with get_db_session() as db:
        existing = db.execute(select(Admin).where(Admin.email == email)).scalar_one_or_none()
        if existing is not None:
            print(f"admin already exists: {email}", file=sys.stderr)
            return 1
        db.add(Admin(email=email, password_hash=hash_password(password)))
        db.commit()

    print(f"created admin: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
