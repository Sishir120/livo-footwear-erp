"""015_sales_dispatch_and_expenses

Revision ID: 015_sales_dispatch_and_expenses
Revises: 014_raw_material_ledger_and_landed_cost
Create Date: 2026-10-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '015_sales_dispatch_and_expenses'
down_revision: Union[str, Sequence[str], None] = '014_raw_material_ledger_and_landed_cost'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)

    # 1. Add dispatch metadata columns to sales_orders if not present
    sales_orders_cols = {c['name'] for c in inspector.get_columns('sales_orders')}
    
    new_cols = [
        ('dispatched_at', sa.DateTime(timezone=True), None, True),
        ('dispatch_notes', sa.String(length=255), None, True),
        ('carrier_name', sa.String(length=128), None, True),
        ('vehicle_number', sa.String(length=64), None, True),
    ]

    for col_name, col_type, s_default, is_null in new_cols:
        if col_name not in sales_orders_cols:
            op.add_column('sales_orders', sa.Column(col_name, col_type, server_default=s_default, nullable=is_null))

    if 'dispatched_by_id' not in sales_orders_cols:
        if conn.dialect.name == 'sqlite':
            op.add_column('sales_orders', sa.Column('dispatched_by_id', sa.Integer(), nullable=True))
        else:
            op.add_column('sales_orders', sa.Column('dispatched_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

    # 2. Create sales_expenses table if not exists
    tables = set(inspector.get_table_names())
    if 'sales_expenses' not in tables:
        op.create_table(
            'sales_expenses',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('expense_date_ad', sa.Date(), nullable=False),
            sa.Column('expense_date_bs', sa.String(length=10), nullable=False),
            sa.Column('particular', sa.String(length=255), nullable=False),
            sa.Column('category', sa.String(length=32), nullable=False),
            sa.Column('amount_paisa', sa.BigInteger(), nullable=False),
            sa.Column('sales_order_id', sa.Integer(), sa.ForeignKey('sales_orders.id'), nullable=True, index=True),
            sa.Column('payment_method', sa.String(length=32), nullable=False, server_default='CASH'),
            sa.Column('remarks', sa.String(length=255), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("amount_paisa > 0", name="chk_sales_expense_amount_positive"),
            sa.CheckConstraint(
                "category IN ('DELIVERY_FREIGHT', 'PACKING_MATERIALS', 'SALES_COMMISSION', 'LOADING_UNLOADING', 'PROMOTIONAL_SAMPLE', 'OTHER')",
                name="chk_sales_expense_category"
            ),
            sa.CheckConstraint("payment_method IN ('CASH', 'BANK')", name="chk_sales_expense_payment_method")
        )
        op.create_index(
            'ix_sales_expenses_company_date',
            'sales_expenses',
            ['company_id', 'expense_date_ad']
        )


def downgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)

    tables = set(inspector.get_table_names())
    if 'sales_expenses' in tables:
        indexes = {i['name'] for i in inspector.get_indexes('sales_expenses')}
        if 'ix_sales_expenses_company_date' in indexes:
            op.drop_index('ix_sales_expenses_company_date', table_name='sales_expenses')
        op.drop_table('sales_expenses')

    sales_orders_cols = {c['name'] for c in inspector.get_columns('sales_orders')}
    cols_to_drop = [
        'dispatched_at',
        'dispatched_by_id',
        'dispatch_notes',
        'carrier_name',
        'vehicle_number',
    ]

    for col in cols_to_drop:
        if col in sales_orders_cols:
            op.drop_column('sales_orders', col)
