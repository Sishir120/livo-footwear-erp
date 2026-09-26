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
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.create_unique_constraint('uq_invoice_company_sequence', ['company_id', 'sequence_number'])

def downgrade() -> None:
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_constraint('uq_invoice_company_sequence', type_='unique')
