"""add orthophoto_bbox to flights

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flights", sa.Column("orthophoto_bbox", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("flights", "orthophoto_bbox")
