"""008_hr_management

Revision ID: 008_hr_management
Revises: 007_production_sync_engine
Create Date: 2026-09-29 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_hr_management'
down_revision: Union[str, Sequence[str], None] = '007_production_sync_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Workers table
    if 'workers' not in tables:
        op.create_table(
            'workers',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('worker_code', sa.String(length=32), nullable=False),
            sa.Column('name', sa.String(length=128), nullable=False),
            sa.Column('join_date', sa.Date(), nullable=False),
            sa.Column('pay_type', sa.String(length=16), nullable=False),
            sa.Column('basic_rate_paisa', sa.BigInteger(), nullable=False),
            sa.Column('phone', sa.String(length=32), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('company_id', 'worker_code', name='uq_company_worker_code')
        )
        op.create_index('ix_workers_id', 'workers', ['id'], unique=False)
        op.create_index('ix_workers_company_id', 'workers', ['company_id'], unique=False)
        op.create_index('ix_workers_worker_code', 'workers', ['worker_code'], unique=False)
        op.create_index('ix_workers_is_active', 'workers', ['is_active'], unique=False)
        op.create_index('ix_worker_company_status', 'workers', ['company_id', 'is_active'], unique=False)

    # 2. Worker Advances table
    if 'worker_advances' not in tables:
        op.create_table(
            'worker_advances',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('worker_id', sa.Integer(), sa.ForeignKey('workers.id'), nullable=False),
            sa.Column('amount_paisa', sa.BigInteger(), nullable=False),
            sa.Column('entry_type', sa.String(length=16), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_worker_advances_id', 'worker_advances', ['id'], unique=False)
        op.create_index('ix_worker_advances_company_id', 'worker_advances', ['company_id'], unique=False)
        op.create_index('ix_worker_advances_worker_id', 'worker_advances', ['worker_id'], unique=False)
        op.create_index('ix_advances_worker_date', 'worker_advances', ['company_id', 'worker_id', 'date'], unique=False)

    # 3. Worker Monthly Records table
    if 'worker_monthly_records' not in tables:
        op.create_table(
            'worker_monthly_records',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('worker_id', sa.Integer(), sa.ForeignKey('workers.id'), nullable=False),
            sa.Column('month_year', sa.String(length=10), nullable=False),
            sa.Column('total_working_hours', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('overtime_hours', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('gross_pay_paisa', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('advance_deduction_paisa', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('net_paid_paisa', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('paid_date', sa.Date(), nullable=True),
            sa.Column('payment_method', sa.String(length=32), nullable=True),
            sa.Column('status', sa.String(length=16), server_default='PENDING', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('company_id', 'worker_id', 'month_year', name='uq_worker_monthly_company_month')
        )
        op.create_index('ix_worker_monthly_records_id', 'worker_monthly_records', ['id'], unique=False)
        op.create_index('ix_worker_monthly_records_company_id', 'worker_monthly_records', ['company_id'], unique=False)
        op.create_index('ix_worker_monthly_records_worker_id', 'worker_monthly_records', ['worker_id'], unique=False)
        op.create_index('ix_worker_monthly_records_month_year', 'worker_monthly_records', ['month_year'], unique=False)
        op.create_index('ix_monthly_worker_status', 'worker_monthly_records', ['company_id', 'month_year', 'status'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'worker_monthly_records' in tables:
        op.drop_table('worker_monthly_records')
    if 'worker_advances' in tables:
        op.drop_table('worker_advances')
    if 'workers' in tables:
        op.drop_table('workers')
