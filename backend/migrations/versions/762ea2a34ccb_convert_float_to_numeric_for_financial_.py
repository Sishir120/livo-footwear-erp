"""Convert float to numeric for financial precision

Revision ID: 762ea2a34ccb
Revises: 009_gallery_and_analytics
Create Date: 2026-09-30 13:17:22.885634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '762ea2a34ccb'
down_revision: Union[str, Sequence[str], None] = '009_gallery_and_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'journal_entries' in existing_tables:
        op.drop_table('journal_entries')
    if 'ledger_accounts' in existing_tables:
        op.drop_table('ledger_accounts')
    if 'journal_vouchers' in existing_tables:
        op.drop_table('journal_vouchers')
    if 'account_groups' in existing_tables:
        op.drop_table('account_groups')

    # SQLite does not support ALTER COLUMN TYPE and maintains dynamic type affinity.
    # PostgreSQL executes the exact DDL below.
    if conn.dialect.name == "sqlite":
        return

    op.alter_column('clients', 'credit_limit',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=True)
    op.alter_column('daily_factory_logs', 'total_working_hours',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('daily_factory_logs', 'pairs_per_worker_ratio',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('daily_factory_logs', 'pairs_per_man_hour_ratio',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'subtotal',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'vat_rate',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'vat_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'total_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'received_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('invoices', 'receivable_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    # op.create_unique_constraint('uq_invoice_company_sequence', 'invoices', ['company_id', 'sequence_number'])
    op.alter_column('payment_allocations', 'created_at',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.alter_column('payments', 'amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('production_batches', 'target_quantity',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('production_batches', 'produced_quantity',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('production_material_usage', 'quantity_used',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('production_sync_logs', 'created_at',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.alter_column('products', 'unit_price',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('purchases', 'quantity',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('purchases', 'unit_price',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('purchases', 'total_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('raw_materials', 'min_stock_alert',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=True)
    op.alter_column('receivable_entries', 'occurred_at',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.alter_column('sales_items', 'quantity',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('sales_items', 'unit_price',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('sales_items', 'total_price',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'total_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'received_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'receivable_amount',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('stock_movements', 'quantity',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('worker_monthly_records', 'total_working_hours',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    op.alter_column('worker_monthly_records', 'overtime_hours',
               existing_type=sa.FLOAT(),
               type_=sa.Numeric(),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        return

    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('worker_monthly_records', 'overtime_hours',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('worker_monthly_records', 'total_working_hours',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('stock_movements', 'quantity',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'receivable_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'received_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_orders', 'total_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_items', 'total_price',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_items', 'unit_price',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('sales_items', 'quantity',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('receivable_entries', 'occurred_at',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.alter_column('raw_materials', 'min_stock_alert',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=True)
    op.alter_column('purchases', 'total_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('purchases', 'unit_price',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('purchases', 'quantity',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('products', 'unit_price',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('production_sync_logs', 'created_at',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    op.alter_column('production_material_usage', 'quantity_used',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('production_batches', 'produced_quantity',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('production_batches', 'target_quantity',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('payments', 'amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('payment_allocations', 'created_at',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    # op.drop_constraint('uq_invoice_company_sequence', 'invoices', type_='unique')
    op.alter_column('invoices', 'receivable_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('invoices', 'received_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('invoices', 'total_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('invoices', 'vat_amount',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('invoices', 'vat_rate',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('invoices', 'subtotal',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('daily_factory_logs', 'pairs_per_man_hour_ratio',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('daily_factory_logs', 'pairs_per_worker_ratio',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('daily_factory_logs', 'total_working_hours',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=False)
    op.alter_column('clients', 'credit_limit',
               existing_type=sa.Numeric(),
               type_=sa.FLOAT(),
               existing_nullable=True)
    op.create_table('journal_vouchers',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('company_id', sa.INTEGER(), nullable=False),
    sa.Column('voucher_number', sa.VARCHAR(length=50), nullable=False),
    sa.Column('voucher_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('date_ad', sa.VARCHAR(length=10), nullable=False),
    sa.Column('date_bs', sa.VARCHAR(length=10), nullable=False),
    sa.Column('narration', sa.TEXT(), nullable=True),
    sa.Column('ref_type', sa.VARCHAR(length=50), nullable=True),
    sa.Column('ref_id', sa.INTEGER(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_journal_vouchers_voucher_number'), 'journal_vouchers', ['voucher_number'], unique=False)
    op.create_index(op.f('ix_journal_vouchers_id'), 'journal_vouchers', ['id'], unique=False)
    op.create_index(op.f('ix_journal_vouchers_date_ad'), 'journal_vouchers', ['date_ad'], unique=False)
    op.create_index(op.f('ix_journal_vouchers_company_id'), 'journal_vouchers', ['company_id'], unique=False)
    op.create_table('ledger_accounts',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('company_id', sa.INTEGER(), nullable=False),
    sa.Column('group_id', sa.INTEGER(), nullable=False),
    sa.Column('code', sa.VARCHAR(length=50), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('opening_balance', sa.FLOAT(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['account_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_accounts_id'), 'ledger_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_ledger_accounts_group_id'), 'ledger_accounts', ['group_id'], unique=False)
    op.create_index(op.f('ix_ledger_accounts_company_id'), 'ledger_accounts', ['company_id'], unique=False)
    op.create_index(op.f('ix_ledger_accounts_code'), 'ledger_accounts', ['code'], unique=False)
    op.create_table('account_groups',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('company_id', sa.INTEGER(), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('group_type', sa.VARCHAR(length=50), nullable=False),
    sa.Column('parent_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['account_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_groups_id'), 'account_groups', ['id'], unique=False)
    op.create_index(op.f('ix_account_groups_company_id'), 'account_groups', ['company_id'], unique=False)
    op.create_table('journal_entries',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('company_id', sa.INTEGER(), nullable=False),
    sa.Column('voucher_id', sa.INTEGER(), nullable=False),
    sa.Column('ledger_id', sa.INTEGER(), nullable=False),
    sa.Column('debit_amount', sa.FLOAT(), nullable=True),
    sa.Column('credit_amount', sa.FLOAT(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['ledger_id'], ['ledger_accounts.id'], ),
    sa.ForeignKeyConstraint(['voucher_id'], ['journal_vouchers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_journal_entries_voucher_id'), 'journal_entries', ['voucher_id'], unique=False)
    op.create_index(op.f('ix_journal_entries_ledger_id'), 'journal_entries', ['ledger_id'], unique=False)
    op.create_index(op.f('ix_journal_entries_id'), 'journal_entries', ['id'], unique=False)
    op.create_index(op.f('ix_journal_entries_company_id'), 'journal_entries', ['company_id'], unique=False)
    # ### end Alembic commands ###
