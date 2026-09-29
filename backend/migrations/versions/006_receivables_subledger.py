"""006_receivables_subledger

Revision ID: 006_receivables_subledger
Revises: 005_stock_card_ledger
Create Date: 2026-09-29 09:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_receivables_subledger'
down_revision: Union[str, Sequence[str], None] = '005_stock_card_ledger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create receivable_entries table
    if 'receivable_entries' not in tables:
        op.create_table(
            'receivable_entries',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
            sa.Column('entry_type', sa.String(length=32), nullable=False),
            sa.Column('direction', sa.Integer(), nullable=False),
            sa.Column('amount_paisa', sa.BigInteger(), nullable=False),
            sa.Column('source_doc_ref', sa.String(length=64), nullable=True),
            sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_disputed', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('dispute_notes', sa.String(length=255), nullable=True),
            sa.Column('notes', sa.String(length=255), nullable=True)
        )
        op.create_index('ix_receivable_entries_id', 'receivable_entries', ['id'], unique=False)
        op.create_index('ix_receivable_entries_company_id', 'receivable_entries', ['company_id'], unique=False)
        op.create_index('ix_receivable_entries_client_id', 'receivable_entries', ['client_id'], unique=False)
        op.create_index('ix_receivable_entries_entry_type', 'receivable_entries', ['entry_type'], unique=False)
        op.create_index('ix_receivable_entries_source_doc_ref', 'receivable_entries', ['source_doc_ref'], unique=False)
        op.create_index('ix_receivable_entries_invoice_id', 'receivable_entries', ['invoice_id'], unique=False)
        op.create_index('ix_receivable_entries_occurred_at', 'receivable_entries', ['occurred_at'], unique=False)
        op.create_index('ix_ar_party_date', 'receivable_entries', ['company_id', 'client_id', 'occurred_at'], unique=False)

    # 2. Create payment_allocations table
    if 'payment_allocations' not in tables:
        op.create_table(
            'payment_allocations',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('payment_entry_id', sa.Integer(), sa.ForeignKey('receivable_entries.id'), nullable=False),
            sa.Column('invoice_entry_id', sa.Integer(), sa.ForeignKey('receivable_entries.id'), nullable=False),
            sa.Column('allocated_paisa', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_payment_allocations_id', 'payment_allocations', ['id'], unique=False)
        op.create_index('ix_payment_allocations_company_id', 'payment_allocations', ['company_id'], unique=False)
        op.create_index('ix_payment_allocations_payment_entry_id', 'payment_allocations', ['payment_entry_id'], unique=False)
        op.create_index('ix_payment_allocations_invoice_entry_id', 'payment_allocations', ['invoice_entry_id'], unique=False)

def downgrade() -> None:
    op.drop_table('payment_allocations')
    op.drop_table('receivable_entries')
