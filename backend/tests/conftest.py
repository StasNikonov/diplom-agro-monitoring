"""Shared fixtures for pytest test suite."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app


def _db_url() -> str:
    user = os.environ.get("POSTGRES_USER", "agro")
    password = os.environ.get("POSTGRES_PASSWORD", "agro")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "agrodb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def engine():
    return create_engine(_db_url())


@pytest.fixture(scope="session")
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def db(engine):
    """Per-test transaction that rolls back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = create_access_token("admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def authed_client(client, auth_headers):
    client.headers.update(auth_headers)
    return client
