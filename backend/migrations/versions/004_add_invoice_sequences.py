"""004_add_invoice_sequences

Revision ID: 004_invoice_sequences
Revises: 003_snapshots_bom
Create Date: 2026-09-29 07:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_invoice_sequences'
down_revision: Union[str, Sequence[str], None] = '003_snapshots_bom'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'invoice_sequences',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('current_sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('company_id', name='uq_invoice_sequences_company')
    )
    op.create_index('ix_invoice_sequences_id', 'invoice_sequences', ['id'], unique=False)
    op.create_index('ix_invoice_sequences_company_id', 'invoice_sequences', ['company_id'], unique=True)

def downgrade() -> None:
    op.drop_table('invoice_sequences')
