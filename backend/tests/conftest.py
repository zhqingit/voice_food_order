import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


def _make_client(*, base_url: str):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app, base_url=base_url)


@pytest.fixture()
def user_client():
    with _make_client(base_url="http://user-api.local") as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()


@pytest.fixture()
def store_client():
    with _make_client(base_url="http://store-api.local") as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()
