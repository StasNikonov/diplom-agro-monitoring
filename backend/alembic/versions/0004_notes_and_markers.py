"""add notes to flights and field_markers table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flights', sa.Column('notes', sa.Text(), nullable=True, server_default=''))

    op.create_table(
        'field_markers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('field_id', UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True, server_default=''),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('field_markers')
    op.drop_column('flights', 'notes')
