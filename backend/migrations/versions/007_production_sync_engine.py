"""007_production_sync_engine

Revision ID: 007_production_sync_engine
Revises: 006_receivables_subledger
Create Date: 2026-09-29 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_production_sync_engine'
down_revision: Union[str, Sequence[str], None] = '006_receivables_subledger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'production_sync_logs' not in tables:
        op.create_table(
            'production_sync_logs',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('idempotency_key', sa.String(length=128), nullable=False),
            sa.Column('batch_id', sa.Integer(), sa.ForeignKey('production_batches.id'), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('payload_hash', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('error_code', sa.String(length=64), nullable=True),
            sa.Column('error_message', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_production_sync_logs_id', 'production_sync_logs', ['id'], unique=False)
        op.create_index('ix_production_sync_logs_company_id', 'production_sync_logs', ['company_id'], unique=False)
        op.create_index('ix_production_sync_logs_idempotency_key', 'production_sync_logs', ['idempotency_key'], unique=True)
        op.create_index('ix_sync_company_key', 'production_sync_logs', ['company_id', 'idempotency_key'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'production_sync_logs' in tables:
        op.drop_table('production_sync_logs')
