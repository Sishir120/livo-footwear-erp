"""002_add_invoice_unique_constraint

Revision ID: 002_invoice_uq
Revises: 001_baseline
Create Date: 2026-09-26 08:36:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_invoice_uq'
down_revision: Union[str, Sequence[str], None] = '001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # DB-level UNIQUE constraint on (company_id, sequence_number) on invoices table (RULES.md §3)
    # Uses idempotent pattern for PostgreSQL: ignores duplicate_object if constraint already exists.
    # SQLite requires batch_alter_table to add constraints.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table('invoices') as batch_op:
            batch_op.create_unique_constraint('uq_invoice_company_sequence', ['company_id', 'sequence_number'])
    else:
        # PostgreSQL: idempotent constraint creation (handles pre-existing constraint from create_all)
        bind.execute(sa.text("""
            DO $$
            BEGIN
                ALTER TABLE invoices
                    ADD CONSTRAINT uq_invoice_company_sequence UNIQUE (company_id, sequence_number);
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN duplicate_table THEN NULL;
            END
            $$
        """))

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table('invoices') as batch_op:
            batch_op.drop_constraint('uq_invoice_company_sequence', type_='unique')
    else:
        bind.execute(sa.text(
            "ALTER TABLE invoices DROP CONSTRAINT IF EXISTS uq_invoice_company_sequence"
        ))
