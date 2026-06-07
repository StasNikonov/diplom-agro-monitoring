import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, server_default="employee")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

TZ = TIMESTAMP(timezone=True)


class Field(Base):
    __tablename__ = "fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    boundary = Column(Geometry("POLYGON", srid=4326))
    area_ha = Column(Float)
    created_at = Column(TZ, server_default=func.now())

    flights = relationship("Flight", back_populates="field", lazy="select")
    markers = relationship("FieldMarker", back_populates="field", lazy="select", cascade="all, delete-orphan")


class Flight(Base):
    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"))
    flown_at = Column(TZ, nullable=False)
    raw_path = Column(Text)
    status = Column(String(50), default="uploaded")
    odm_task_uuid = Column(Text)
    rq_job_id = Column(Text)
    orthophoto_bbox = Column(Text)   # JSON: [west, south, east, north]
    notes = Column(Text, default="")
    created_at = Column(TZ, server_default=func.now())

    field = relationship("Field", back_populates="flights")
    index_maps = relationship("IndexMap", back_populates="flight", lazy="select")
    anomaly_zones = relationship("AnomalyZone", back_populates="flight", lazy="select")


class IndexMap(Base):
    __tablename__ = "index_maps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id", ondelete="CASCADE"))
    index_type = Column(String(10), nullable=False)
    file_path = Column(Text, nullable=False)
    min_value = Column(Float)
    max_value = Column(Float)
    mean_value = Column(Float)
    created_at = Column(TZ, server_default=func.now())

    flight = relationship("Flight", back_populates="index_maps")


class FieldMarker(Base):
    __tablename__ = "field_markers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"))
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    note = Column(Text, default="")
    created_at = Column(TZ, server_default=func.now())

    field = relationship("Field", back_populates="markers")


class AnomalyZone(Base):
    __tablename__ = "anomaly_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id", ondelete="CASCADE"))
    index_type = Column(String(10), nullable=False)
    zone_geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    threshold = Column(Float)
    area_ha = Column(Float)
    created_at = Column(TZ, server_default=func.now())

    flight = relationship("Flight", back_populates="anomaly_zones")
