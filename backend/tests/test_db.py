"""Integration test: Field model round-trip against a real PostGIS database."""
import os

import pytest
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import box
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Field


def _db_url() -> str:
    user = os.environ.get("POSTGRES_USER", "agro")
    password = os.environ.get("POSTGRES_PASSWORD", "agro")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "agrodb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(_db_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_field_geometry_roundtrip(db_session):
    # Simple 1°×1° rectangle near Kyiv
    rect = box(30.0, 50.0, 31.0, 51.0)
    field = Field(name="Test Field", boundary=from_shape(rect, srid=4326), area_ha=100.0)

    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    assert field.id is not None

    saved = db_session.get(Field, field.id)
    assert saved is not None
    assert saved.name == "Test Field"

    shape = to_shape(saved.boundary)
    assert shape.geom_type == "Polygon"
    assert abs(shape.bounds[0] - 30.0) < 1e-6

    db_session.delete(saved)
    db_session.commit()

    assert db_session.get(Field, field.id) is None
