"""010_client_change_requests_core

Revision ID: 010_client_change_requests_core
Revises: 009_gallery_and_analytics
Create Date: 2026-10-11 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '010_client_change_requests_core'
down_revision: Union[str, Sequence[str], None] = '009_gallery_and_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)

    # 1. Update raw_materials
    raw_materials_cols = {c['name'] for c in inspector.get_columns('raw_materials')}
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('raw_materials') as batch_op:
            if 'reorder_level' not in raw_materials_cols:
                batch_op.add_column(sa.Column('reorder_level', sa.Float(), server_default='0.0', nullable=False))
            if 'current_stock' not in raw_materials_cols:
                batch_op.add_column(sa.Column('current_stock', sa.Float(), server_default='0.0', nullable=False))
    else:
        if 'reorder_level' not in raw_materials_cols:
            op.add_column('raw_materials', sa.Column('reorder_level', sa.Float(), server_default='0.0', nullable=False))
        if 'current_stock' not in raw_materials_cols:
            op.add_column('raw_materials', sa.Column('current_stock', sa.Float(), server_default='0.0', nullable=False))

    # Normalize existing units before adding CHECK constraint
    op.execute(sa.text("UPDATE raw_materials SET unit = 'kg' WHERE unit NOT IN ('kg', 'pcs', 'litre') OR unit IS NULL"))

    existing_constraints = {c['name'] for c in inspector.get_check_constraints('raw_materials')}
    if 'chk_raw_material_unit' not in existing_constraints:
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('raw_materials') as batch_op:
                batch_op.create_check_constraint('chk_raw_material_unit', "unit IN ('kg', 'pcs', 'litre')")
        else:
            op.create_check_constraint('chk_raw_material_unit', 'raw_materials', "unit IN ('kg', 'pcs', 'litre')")

    # 2. Update purchases
    purchases_cols = {c['name'] for c in inspector.get_columns('purchases')}
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('purchases') as batch_op:
            if 'order_date_ad' not in purchases_cols:
                batch_op.add_column(sa.Column('order_date_ad', sa.Date(), nullable=True))
            if 'order_date_bs' not in purchases_cols:
                batch_op.add_column(sa.Column('order_date_bs', sa.String(length=10), nullable=True))
            if 'receipt_date_ad' not in purchases_cols:
                batch_op.add_column(sa.Column('receipt_date_ad', sa.Date(), nullable=True))
            if 'receipt_date_bs' not in purchases_cols:
                batch_op.add_column(sa.Column('receipt_date_bs', sa.String(length=10), nullable=True))
            if 'status' not in purchases_cols:
                batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='RECEIVED', nullable=False))
    else:
        if 'order_date_ad' not in purchases_cols:
            op.add_column('purchases', sa.Column('order_date_ad', sa.Date(), nullable=True))
        if 'order_date_bs' not in purchases_cols:
            op.add_column('purchases', sa.Column('order_date_bs', sa.String(length=10), nullable=True))
        if 'receipt_date_ad' not in purchases_cols:
            op.add_column('purchases', sa.Column('receipt_date_ad', sa.Date(), nullable=True))
        if 'receipt_date_bs' not in purchases_cols:
            op.add_column('purchases', sa.Column('receipt_date_bs', sa.String(length=10), nullable=True))
        if 'status' not in purchases_cols:
            op.add_column('purchases', sa.Column('status', sa.String(length=20), server_default='RECEIVED', nullable=False))

    # 3. Update sales_orders
    sales_cols = {c['name'] for c in inspector.get_columns('sales_orders')}
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('sales_orders') as batch_op:
            if 'dispatch_date_ad' not in sales_cols:
                batch_op.add_column(sa.Column('dispatch_date_ad', sa.Date(), nullable=True))
            if 'dispatch_date_bs' not in sales_cols:
                batch_op.add_column(sa.Column('dispatch_date_bs', sa.String(length=10), nullable=True))
    else:
        if 'dispatch_date_ad' not in sales_cols:
            op.add_column('sales_orders', sa.Column('dispatch_date_ad', sa.Date(), nullable=True))
        if 'dispatch_date_bs' not in sales_cols:
            op.add_column('sales_orders', sa.Column('dispatch_date_bs', sa.String(length=10), nullable=True))

    # Backward compatibility: map delivered orders to DISPATCHED
    if conn.dialect.name == 'sqlite':
        op.execute(sa.text("UPDATE sales_orders SET status = 'DISPATCHED' WHERE delivered = 1"))
    else:
        op.execute(sa.text("UPDATE sales_orders SET status = 'DISPATCHED' WHERE delivered IS TRUE"))

    # 4. Update workers
    workers_cols = {c['name'] for c in inspector.get_columns('workers')}
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('workers') as batch_op:
            if 'photo_url' not in workers_cols:
                batch_op.add_column(sa.Column('photo_url', sa.String(length=512), nullable=True))
            if 'temporary_address' not in workers_cols:
                batch_op.add_column(sa.Column('temporary_address', sa.String(length=255), nullable=True))
            if 'permanent_address' not in workers_cols:
                batch_op.add_column(sa.Column('permanent_address', sa.String(length=255), nullable=True))
            if 'inactive_date' not in workers_cols:
                batch_op.add_column(sa.Column('inactive_date', sa.Date(), nullable=True))
            if 'inactive_reason' not in workers_cols:
                batch_op.add_column(sa.Column('inactive_reason', sa.String(length=255), nullable=True))
    else:
        if 'photo_url' not in workers_cols:
            op.add_column('workers', sa.Column('photo_url', sa.String(length=512), nullable=True))
        if 'temporary_address' not in workers_cols:
            op.add_column('workers', sa.Column('temporary_address', sa.String(length=255), nullable=True))
        if 'permanent_address' not in workers_cols:
            op.add_column('workers', sa.Column('permanent_address', sa.String(length=255), nullable=True))
        if 'inactive_date' not in workers_cols:
            op.add_column('workers', sa.Column('inactive_date', sa.Date(), nullable=True))
        if 'inactive_reason' not in workers_cols:
            op.add_column('workers', sa.Column('inactive_reason', sa.String(length=255), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('workers') as batch_op:
            batch_op.drop_column('inactive_reason')
            batch_op.drop_column('inactive_date')
            batch_op.drop_column('permanent_address')
            batch_op.drop_column('temporary_address')
            batch_op.drop_column('photo_url')

        with op.batch_alter_table('sales_orders') as batch_op:
            batch_op.drop_column('dispatch_date_bs')
            batch_op.drop_column('dispatch_date_ad')

        with op.batch_alter_table('purchases') as batch_op:
            batch_op.drop_column('status')
            batch_op.drop_column('receipt_date_bs')
            batch_op.drop_column('receipt_date_ad')
            batch_op.drop_column('order_date_bs')
            batch_op.drop_column('order_date_ad')

        with op.batch_alter_table('raw_materials') as batch_op:
            try:
                batch_op.drop_constraint('chk_raw_material_unit', type_='check')
            except Exception:
                pass
            batch_op.drop_column('current_stock')
            batch_op.drop_column('reorder_level')
    else:
        op.drop_column('workers', 'inactive_reason')
        op.drop_column('workers', 'inactive_date')
        op.drop_column('workers', 'permanent_address')
        op.drop_column('workers', 'temporary_address')
        op.drop_column('workers', 'photo_url')

        op.drop_column('sales_orders', 'dispatch_date_bs')
        op.drop_column('sales_orders', 'dispatch_date_ad')

        op.drop_column('purchases', 'status')
        op.drop_column('purchases', 'receipt_date_bs')
        op.drop_column('purchases', 'receipt_date_ad')
        op.drop_column('purchases', 'order_date_bs')
        op.drop_column('purchases', 'order_date_ad')

        try:
            op.drop_constraint('chk_raw_material_unit', 'raw_materials', type_='check')
        except Exception:
            pass
        op.drop_column('raw_materials', 'current_stock')
        op.drop_column('raw_materials', 'reorder_level')
