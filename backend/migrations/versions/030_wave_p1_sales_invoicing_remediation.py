"""030_wave_p1_sales_invoicing_remediation

Revision ID: 030_wave_p1_sales_invoicing_remediation
Revises: 029_add_pan_number_to_parties
Create Date: 2026-10-21 09:15:00.000000

Wave P1.1 Acceptance Remediation:
1. Alters invoices.sequence_number to nullable=True, permitting multiple
   unfinalized draft invoices per company without violating uq_invoice_company_sequence.
2. Creates credit_notes and credit_note_items tables to authoritatively track
   commercial sales returns and cumulative returned quantities per invoice line,
   decoupling commercial credit tracking from physical stock movements.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '030_wave_p1_sales_invoicing_remediation'
down_revision: Union[str, Sequence[str], None] = '029_add_pan_number_to_parties'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # 1. Alter invoices.sequence_number to nullable=True
    if 'invoices' in tables:
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('invoices') as batch_op:
                batch_op.alter_column('sequence_number', existing_type=sa.Integer(), nullable=True)
        else:
            op.alter_column('invoices', 'sequence_number', existing_type=sa.Integer(), nullable=True)

    # 2. Create credit_notes table
    if 'credit_notes' not in tables:
        op.create_table(
            'credit_notes',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False, index=True),
            sa.Column('receivable_entry_id', sa.Integer(), sa.ForeignKey('receivable_entries.id'), nullable=True, index=True),
            sa.Column('credit_note_number', sa.String(50), nullable=False, index=True),
            sa.Column('date_ad', sa.String(10), nullable=False),
            sa.Column('date_bs', sa.String(10), nullable=False),
            sa.Column('reason', sa.String(255), nullable=False),
            sa.Column('taxable_amount_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('vat_amount_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_amount_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('return_to_stock', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.UniqueConstraint('company_id', 'credit_note_number', name='uq_credit_note_company_number')
        )

    # 3. Create credit_note_items table
    if 'credit_note_items' not in tables:
        op.create_table(
            'credit_note_items',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('credit_note_id', sa.Integer(), sa.ForeignKey('credit_notes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
            sa.Column('quantity', sa.Numeric(), nullable=False),
            sa.Column('unit_price_paisa', sa.Integer(), nullable=False),
            sa.Column('discount_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('taxable_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('vat_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_paisa', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('return_to_stock', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'credit_note_items' in tables:
        op.drop_table('credit_note_items')

    if 'credit_notes' in tables:
        op.drop_table('credit_notes')

    if 'invoices' in tables:
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('invoices') as batch_op:
                batch_op.alter_column('sequence_number', existing_type=sa.Integer(), nullable=False)
        else:
            op.alter_column('invoices', 'sequence_number', existing_type=sa.Integer(), nullable=False)
