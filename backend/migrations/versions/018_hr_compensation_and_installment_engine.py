"""018_hr_compensation_and_installment_engine

Revision ID: 018_hr_compensation_and_installment_engine
Revises: 017_hr_worker_citizenship
Create Date: 2026-10-12

Phase 4B.4.1: Company HR settings, worker compensation overrides, and monthly payroll snapshots.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '018_hr_compensation_and_installment_engine'
down_revision: Union[str, None] = '017_hr_worker_citizenship'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create company_hr_settings table if not exists
    if 'company_hr_settings' not in tables:
        op.create_table(
            'company_hr_settings',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('standard_monthly_hours', sa.Numeric(precision=6, scale=2), nullable=False, server_default='208.00'),
            sa.Column('overtime_multiplier', sa.Numeric(precision=4, scale=2), nullable=False, server_default='1.50'),
            sa.Column('max_advance_deduction_pct', sa.Integer(), nullable=True, server_default='50'),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.UniqueConstraint('company_id', name='uq_company_hr_settings_company')
        )

    # 2. Add worker overrides to workers table
    workers_cols = {c['name'] for c in inspector.get_columns('workers')}
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('workers') as batch_op:
            if 'standard_monthly_hours_override' not in workers_cols:
                batch_op.add_column(sa.Column('standard_monthly_hours_override', sa.Numeric(precision=6, scale=2), nullable=True))
            if 'overtime_rate_paisa_override' not in workers_cols:
                batch_op.add_column(sa.Column('overtime_rate_paisa_override', sa.BigInteger(), nullable=True))
    else:
        if 'standard_monthly_hours_override' not in workers_cols:
            op.add_column('workers', sa.Column('standard_monthly_hours_override', sa.Numeric(precision=6, scale=2), nullable=True))
        if 'overtime_rate_paisa_override' not in workers_cols:
            op.add_column('workers', sa.Column('overtime_rate_paisa_override', sa.BigInteger(), nullable=True))

    # 3. Add snapshot columns to worker_monthly_records table
    monthly_cols = {c['name'] for c in inspector.get_columns('worker_monthly_records')}
    snapshot_fields = [
        ('basic_rate_paisa_snapshot', sa.BigInteger()),
        ('standard_hours_snapshot', sa.Numeric(precision=6, scale=2)),
        ('overtime_multiplier_snapshot', sa.Numeric(precision=4, scale=2)),
        ('overtime_rate_paisa_snapshot', sa.BigInteger()),
        ('regular_pay_paisa', sa.BigInteger()),
        ('overtime_pay_paisa', sa.BigInteger()),
        ('ceiling_pct_snapshot', sa.Integer()),
    ]

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('worker_monthly_records') as batch_op:
            for col_name, col_type in snapshot_fields:
                if col_name not in monthly_cols:
                    batch_op.add_column(sa.Column(col_name, col_type, nullable=True))
    else:
        for col_name, col_type in snapshot_fields:
            if col_name not in monthly_cols:
                op.add_column('worker_monthly_records', sa.Column(col_name, col_type, nullable=True))

    # 4. Auto-provision default settings for all existing companies
    conn.execute(sa.text("""
        INSERT INTO company_hr_settings (company_id, standard_monthly_hours, overtime_multiplier, max_advance_deduction_pct)
        SELECT id, 208.00, 1.50, 50 FROM companies
        WHERE id NOT IN (SELECT company_id FROM company_hr_settings)
    """))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    # Drop snapshot columns from worker_monthly_records
    if 'worker_monthly_records' in tables:
        monthly_cols = {c['name'] for c in inspector.get_columns('worker_monthly_records')}
        cols_to_drop = [
            'basic_rate_paisa_snapshot',
            'standard_hours_snapshot',
            'overtime_multiplier_snapshot',
            'overtime_rate_paisa_snapshot',
            'regular_pay_paisa',
            'overtime_pay_paisa',
            'ceiling_pct_snapshot'
        ]
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('worker_monthly_records') as batch_op:
                for col_name in cols_to_drop:
                    if col_name in monthly_cols:
                        batch_op.drop_column(col_name)
        else:
            for col_name in cols_to_drop:
                if col_name in monthly_cols:
                    op.drop_column('worker_monthly_records', col_name)

    # Drop override columns from workers
    if 'workers' in tables:
        workers_cols = {c['name'] for c in inspector.get_columns('workers')}
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('workers') as batch_op:
                if 'overtime_rate_paisa_override' in workers_cols:
                    batch_op.drop_column('overtime_rate_paisa_override')
                if 'standard_monthly_hours_override' in workers_cols:
                    batch_op.drop_column('standard_monthly_hours_override')
        else:
            if 'overtime_rate_paisa_override' in workers_cols:
                op.drop_column('workers', 'overtime_rate_paisa_override')
            if 'standard_monthly_hours_override' in workers_cols:
                op.drop_column('workers', 'standard_monthly_hours_override')

    # Drop company_hr_settings table
    if 'company_hr_settings' in tables:
        op.drop_table('company_hr_settings')
