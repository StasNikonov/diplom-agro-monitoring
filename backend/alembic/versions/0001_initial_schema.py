"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

TZ = sa.TIMESTAMP(timezone=True)

# spatial_index=False — we create the indexes explicitly below;
# GeoAlchemy2 would auto-generate them with the same names and cause a conflict.
_NO_SIDX = {"spatial_index": False}

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("boundary", geoalchemy2.types.Geometry("POLYGON", srid=4326, **_NO_SIDX), nullable=True),
        sa.Column("area_ha", sa.Float(), nullable=True),
        sa.Column("created_at", TZ, server_default=sa.text("now()"), nullable=True),
    )

    op.create_table(
        "flights",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fields.id", ondelete="CASCADE"), nullable=True),
        sa.Column("flown_at", TZ, nullable=False),
        sa.Column("raw_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="uploaded", nullable=True),
        sa.Column("created_at", TZ, server_default=sa.text("now()"), nullable=True),
    )

    op.create_table(
        "index_maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("flight_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flights.id", ondelete="CASCADE"), nullable=True),
        sa.Column("index_type", sa.String(10), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("created_at", TZ, server_default=sa.text("now()"), nullable=True),
    )

    op.create_table(
        "anomaly_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("flight_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flights.id", ondelete="CASCADE"), nullable=True),
        sa.Column("index_type", sa.String(10), nullable=False),
        sa.Column("zone_geom", geoalchemy2.types.Geometry("MULTIPOLYGON", srid=4326, **_NO_SIDX), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("area_ha", sa.Float(), nullable=True),
        sa.Column("created_at", TZ, server_default=sa.text("now()"), nullable=True),
    )

    op.create_index("idx_fields_boundary", "fields", ["boundary"], postgresql_using="gist")
    op.create_index("idx_anomaly_zones_geom", "anomaly_zones", ["zone_geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_anomaly_zones_geom", table_name="anomaly_zones")
    op.drop_index("idx_fields_boundary", table_name="fields")
    op.drop_table("anomaly_zones")
    op.drop_table("index_maps")
    op.drop_table("flights")
    op.drop_table("fields")
