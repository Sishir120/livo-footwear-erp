"""013_merge_heads

Revision ID: 013_merge_heads
Revises: 012_add_c15_indexes, 010_client_change_requests_core
Create Date: 2026-10-11 10:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '013_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('012_add_c15_indexes', '010_client_change_requests_core')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))


def downgrade() -> None:
    pass
