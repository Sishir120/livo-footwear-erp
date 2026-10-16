"""022_add_stock_transfers

Revision ID: 022_add_stock_transfers
Revises: 021_add_document_sequences
Create Date: 2026-10-15 12:45:00.000000

Adds stock_transfers and stock_transfer_items tables for multi-warehouse inventory movement
with independent destination goods receipt verification.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '022_add_stock_transfers'
down_revision: Union[str, Sequence[str], None] = '021_add_document_sequences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'stock_transfers' not in tables:
        op.create_table(
            'stock_transfers',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('transfer_number', sa.String(length=50), nullable=False, index=True),
            sa.Column('source_warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=False, index=True),
            sa.Column('destination_warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=False, index=True),
            sa.Column('status', sa.String(length=32), nullable=False, server_default='DRAFT'),
            sa.Column('transfer_date_ad', sa.String(length=10), nullable=False),
            sa.Column('transfer_date_bs', sa.String(length=10), nullable=False),
            sa.Column('dispatch_date_ad', sa.String(length=10), nullable=True),
            sa.Column('dispatch_date_bs', sa.String(length=10), nullable=True),
            sa.Column('receipt_date_ad', sa.String(length=10), nullable=True),
            sa.Column('receipt_date_bs', sa.String(length=10), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('dispatched_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('received_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('carrier_name', sa.String(length=128), nullable=True),
            sa.Column('vehicle_number', sa.String(length=64), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('company_id', 'transfer_number', name='uq_company_transfer_number')
        )
        op.create_index('ix_transfers_source_wh', 'stock_transfers', ['company_id', 'source_warehouse_id'])
        op.create_index('ix_transfers_dest_wh', 'stock_transfers', ['company_id', 'destination_warehouse_id'])
        op.create_index('ix_transfers_status', 'stock_transfers', ['company_id', 'status'])

    if 'stock_transfer_items' not in tables:
        op.create_table(
            'stock_transfer_items',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('transfer_id', sa.Integer(), sa.ForeignKey('stock_transfers.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
            sa.Column('size', sa.String(length=20), nullable=True),
            sa.Column('requested_quantity', sa.Numeric(), nullable=False),
            sa.Column('dispatched_quantity', sa.Numeric(), nullable=False, server_default='0.0'),
            sa.Column('received_quantity', sa.Numeric(), nullable=False, server_default='0.0'),
            sa.Column('discrepancy_quantity', sa.Numeric(), nullable=False, server_default='0.0'),
            sa.Column('discrepancy_reason', sa.String(length=255), nullable=True)
        )
        op.create_index('ix_transfer_items_lookup', 'stock_transfer_items', ['company_id', 'transfer_id', 'product_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'stock_transfer_items' in tables:
        op.drop_table('stock_transfer_items')
    if 'stock_transfers' in tables:
        op.drop_table('stock_transfers')
