import os

# Settings require real-looking secrets; set them before the app is imported.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-" + "x" * 32)
os.environ.setdefault("REFRESH_TOKEN_PEPPER", "test-refresh-pepper-" + "x" * 32)

import contextlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Models use Postgres-only types (JSONB, partial indexes, FOR UPDATE), so tests
# run against a real Postgres database. Its tables are dropped and recreated
# for every test. Example:
#   TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/voxeats_test pytest -q
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture()
def db_engine():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set (tests need Postgres)")
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_factory(session_factory):
    """Same shape as app.db.session.get_db_session, bound to the test DB."""

    @contextlib.contextmanager
    def _factory():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return _factory


def _make_client(session_factory, *, base_url: str):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, base_url=base_url)


@pytest.fixture()
def user_client(session_factory):
    with _make_client(session_factory, base_url="http://user-api.local") as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()


@pytest.fixture()
def store_client(session_factory):
    with _make_client(session_factory, base_url="http://store-api.local") as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()
