"""add odm_task_uuid and rq_job_id to flights

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flights", sa.Column("odm_task_uuid", sa.Text(), nullable=True))
    op.add_column("flights", sa.Column("rq_job_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("flights", "rq_job_id")
    op.drop_column("flights", "odm_task_uuid")
