"""020_fixed_assets_waste_and_expenses

Revision ID: 020_fixed_assets_waste_and_expenses
Revises: 019_advance_installment_recovery_engine
Create Date: 2026-10-12 17:00:00.000000

Adds fixed_assets, waste_records, and factory_expenses tables.
Fulfills client change requirements for Fixed Assets Register (REQ-18),
Waste & Scrap Material Tracking (REQ-19), and General Factory Expenses (REQ-15).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '020_fixed_assets_waste_and_expenses'
down_revision: Union[str, Sequence[str], None] = '019_advance_installment_recovery_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # 1. fixed_assets
    if 'fixed_assets' not in tables:
        op.create_table(
            'fixed_assets',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('asset_code', sa.String(length=50), nullable=False, index=True),
            sa.Column('asset_name', sa.String(length=255), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('purchase_date_ad', sa.Date(), nullable=False),
            sa.Column('purchase_date_bs', sa.String(length=10), nullable=False),
            sa.Column('purchase_cost_paisa', sa.BigInteger(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('remarks', sa.String(length=255), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("purchase_cost_paisa >= 0", name="chk_fixed_asset_cost_non_negative"),
            sa.CheckConstraint("quantity > 0", name="chk_fixed_asset_quantity_positive"),
            sa.UniqueConstraint('company_id', 'asset_code', name='uq_company_asset_code')
        )

    # 2. waste_records
    if 'waste_records' not in tables:
        op.create_table(
            'waste_records',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('waste_date_ad', sa.Date(), nullable=False),
            sa.Column('waste_date_bs', sa.String(length=10), nullable=False),
            sa.Column('waste_type', sa.String(length=32), nullable=False),
            sa.Column('raw_material_id', sa.Integer(), sa.ForeignKey('raw_materials.id'), nullable=True, index=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True, index=True),
            sa.Column('batch_id', sa.Integer(), sa.ForeignKey('production_batches.id'), nullable=True, index=True),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('unit', sa.String(length=20), nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=True),
            sa.Column('disposal_method', sa.String(length=64), nullable=True, server_default='DISCARDED'),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("quantity > 0", name="chk_waste_record_quantity_positive"),
            sa.CheckConstraint("waste_type IN ('RAW_MATERIAL_SCRAP', 'FINISHED_PAIR_REJECT')", name="chk_waste_record_type")
        )

    # 3. factory_expenses
    if 'factory_expenses' not in tables:
        op.create_table(
            'factory_expenses',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('expense_date_ad', sa.Date(), nullable=False),
            sa.Column('expense_date_bs', sa.String(length=10), nullable=False),
            sa.Column('particular', sa.String(length=255), nullable=False),
            sa.Column('category', sa.String(length=32), nullable=False),
            sa.Column('amount_paisa', sa.BigInteger(), nullable=False),
            sa.Column('payment_method', sa.String(length=32), nullable=False, server_default='CASH'),
            sa.Column('remarks', sa.String(length=255), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("amount_paisa > 0", name="chk_factory_expense_amount_positive"),
            sa.CheckConstraint("payment_method IN ('CASH', 'BANK')", name="chk_factory_expense_payment_method")
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'factory_expenses' in tables:
        op.drop_table('factory_expenses')
    if 'waste_records' in tables:
        op.drop_table('waste_records')
    if 'fixed_assets' in tables:
        op.drop_table('fixed_assets')
