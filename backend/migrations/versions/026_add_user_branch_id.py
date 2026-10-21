"""026_add_user_branch_id

Revision ID: 026_add_user_branch_id
Revises: 025_stock_movement_ledger_immutability
Create Date: 2026-10-17 16:00:00.000000

Adds branch_id foreign key and index to users table for location-scoped authorization.
Preserves existing users with nullable branch_id (requiring explicit assignment for operational scoping).
Supports both PostgreSQL and SQLite.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '026_add_user_branch_id'
down_revision: Union[str, Sequence[str], None] = '025_stock_movement_ledger_immutability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'users' in tables:
        columns = {c['name'] for c in inspector.get_columns('users')}
        if 'branch_id' not in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('users') as batch_op:
                    batch_op.add_column(sa.Column('branch_id', sa.Integer(), nullable=True))
                    batch_op.create_foreign_key('fk_users_branch_id', 'branches', ['branch_id'], ['id'])
                    batch_op.create_index('ix_users_branch_id', ['branch_id'])
            else:
                op.add_column('users', sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id', name='fk_users_branch_id'), nullable=True))
                op.create_index('ix_users_branch_id', 'users', ['branch_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'users' in tables:
        columns = {c['name'] for c in inspector.get_columns('users')}
        if 'branch_id' in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('users') as batch_op:
                    batch_op.drop_constraint('fk_users_branch_id', type_='foreignkey')
                    batch_op.drop_index('ix_users_branch_id')
                    batch_op.drop_column('branch_id')
            else:
                op.drop_index('ix_users_branch_id', table_name='users')
                op.drop_constraint('fk_users_branch_id', table_name='users', type_='foreignkey')
                op.drop_column('users', 'branch_id')
