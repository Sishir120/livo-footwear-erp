"""024_add_rate_limit_entries

Revision ID: 024_add_rate_limit_entries
Revises: 023_add_branches_and_warehouse_link
Create Date: 2026-10-16 10:00:00.000000

Adds rate_limit_entries table for shared distributed rate limiting across multi-worker Uvicorn instances.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '024_add_rate_limit_entries'
down_revision: Union[str, Sequence[str], None] = '023_add_branches_and_warehouse_link'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'rate_limit_entries' not in tables:
        op.create_table(
            'rate_limit_entries',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('key', sa.String(length=128), nullable=False, index=True),
            sa.Column('endpoint', sa.String(length=64), nullable=False, index=True),
            sa.Column('timestamp', sa.Float(), nullable=False, index=True)
        )
        op.create_index('ix_rate_limit_lookup', 'rate_limit_entries', ['key', 'endpoint', 'timestamp'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'rate_limit_entries' in tables:
        op.drop_index('ix_rate_limit_lookup', table_name='rate_limit_entries')
        op.drop_table('rate_limit_entries')
