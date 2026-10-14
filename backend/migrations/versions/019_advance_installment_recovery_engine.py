"""019_advance_installment_recovery_engine

Revision ID: 019_advance_installment_recovery_engine
Revises: 018_hr_compensation_and_installment_engine
Create Date: 2026-10-12

Phase 4B.4.2: Advance installment configuration, parent-child recovery linkages,
and partial unique index preventing duplicate recovery per payroll record.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '019_advance_installment_recovery_engine'
down_revision: Union[str, None] = '018_hr_compensation_and_installment_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    adv_cols = {c['name'] for c in inspector.get_columns('worker_advances')}

    # 1. Add columns to worker_advances
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('worker_advances') as batch_op:
            if 'installment_amount_paisa' not in adv_cols:
                batch_op.add_column(sa.Column('installment_amount_paisa', sa.BigInteger(), nullable=True))
            if 'parent_advance_id' not in adv_cols:
                batch_op.add_column(sa.Column('parent_advance_id', sa.Integer(), nullable=True))
            if 'monthly_record_id' not in adv_cols:
                batch_op.add_column(sa.Column('monthly_record_id', sa.Integer(), nullable=True))
            batch_op.create_index('ix_worker_advances_parent_advance_id', ['parent_advance_id'])
            batch_op.create_index('ix_worker_advances_monthly_record_id', ['monthly_record_id'])
    else:
        if 'installment_amount_paisa' not in adv_cols:
            op.add_column('worker_advances', sa.Column('installment_amount_paisa', sa.BigInteger(), nullable=True))
        if 'parent_advance_id' not in adv_cols:
            op.add_column('worker_advances', sa.Column('parent_advance_id', sa.Integer(), sa.ForeignKey('worker_advances.id', ondelete='RESTRICT'), nullable=True))
            op.create_index('ix_worker_advances_parent_advance_id', 'worker_advances', ['parent_advance_id'])
        if 'monthly_record_id' not in adv_cols:
            op.add_column('worker_advances', sa.Column('monthly_record_id', sa.Integer(), sa.ForeignKey('worker_monthly_records.id', ondelete='RESTRICT'), nullable=True))
            op.create_index('ix_worker_advances_monthly_record_id', 'worker_advances', ['monthly_record_id'])

    # 2. Create partial unique index on (monthly_record_id, parent_advance_id) where both are NOT NULL
    # This DDL executes natively and identically on both PostgreSQL and SQLite 3.8+
    op.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_payroll_advance_recovery
        ON worker_advances (monthly_record_id, parent_advance_id)
        WHERE monthly_record_id IS NOT NULL AND parent_advance_id IS NOT NULL;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # 1. Drop partial unique index
    op.execute(sa.text("DROP INDEX IF EXISTS uq_payroll_advance_recovery;"))

    # 2. Drop columns from worker_advances
    if 'worker_advances' in inspector.get_table_names():
        adv_cols = {c['name'] for c in inspector.get_columns('worker_advances')}
        cols_to_drop = ['monthly_record_id', 'parent_advance_id', 'installment_amount_paisa']

        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('worker_advances') as batch_op:
                for col in cols_to_drop:
                    if col in adv_cols:
                        batch_op.drop_column(col)
        else:
            for col in cols_to_drop:
                if col in adv_cols:
                    op.drop_column('worker_advances', col)
