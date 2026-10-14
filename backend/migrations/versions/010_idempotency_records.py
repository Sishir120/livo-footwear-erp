"""Add idempotency_records table and scope production_sync_logs uniqueness

Revision ID: 010_idempotency_records
Revises: 762ea2a34ccb
Create Date: 2026-10-01 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '010_idempotency_records'
down_revision: Union[str, Sequence[str], None] = '762ea2a34ccb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Create idempotency_records table if not present
    if 'idempotency_records' not in existing_tables:
        op.create_table(
            'idempotency_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('request_method', sa.String(length=16), nullable=False),
        sa.Column('request_path', sa.String(length=256), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_headers', sa.Text(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovery_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id', 'idempotency_key', name='uq_idempotency_company_key')
        )
        op.create_index(op.f('ix_idempotency_records_id'), 'idempotency_records', ['id'], unique=False)
        op.create_index(op.f('ix_idempotency_records_company_id'), 'idempotency_records', ['company_id'], unique=False)
        op.create_index(op.f('ix_idempotency_records_user_id'), 'idempotency_records', ['user_id'], unique=False)
        op.create_index(op.f('ix_idempotency_records_idempotency_key'), 'idempotency_records', ['idempotency_key'], unique=False)
        op.create_index('ix_idempotency_company_key', 'idempotency_records', ['company_id', 'idempotency_key'], unique=False)
        op.create_index('ix_idempotency_status_locked', 'idempotency_records', ['status', 'locked_until'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_idempotency_status_locked', table_name='idempotency_records')
    op.drop_index('ix_idempotency_company_key', table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_idempotency_key'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_user_id'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_company_id'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_id'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
