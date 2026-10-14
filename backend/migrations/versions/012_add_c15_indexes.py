"""Add C15 indexes

Revision ID: 012_add_c15_indexes
Revises: 762ea2a34ccb
Create Date: 2026-10-02 11:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '012_add_c15_indexes'
down_revision: Union[str, Sequence[str], None] = '010_idempotency_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. ix_sales_orders_client on (company_id, client_id)
    op.create_index('ix_sales_orders_client', 'sales_orders', ['company_id', 'client_id'])
    
    # 2. ix_sales_items_order on (company_id, sales_order_id)
    op.create_index('ix_sales_items_order', 'sales_items', ['company_id', 'sales_order_id'])
    
    # 3. ix_stock_snapshot_lookup on (company_id, product_id)
    op.create_index('ix_stock_snapshot_lookup', 'stock_snapshots', ['company_id', 'product_id'])

def downgrade() -> None:
    op.drop_index('ix_stock_snapshot_lookup', table_name='stock_snapshots')
    op.drop_index('ix_sales_items_order', table_name='sales_items')
    op.drop_index('ix_sales_orders_client', table_name='sales_orders')
