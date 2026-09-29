"""003_add_stock_snapshots_and_bom

Revision ID: 003_snapshots_bom
Revises: 002_invoice_uq
Create Date: 2026-09-28 08:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_snapshots_bom'
down_revision: Union[str, Sequence[str], None] = '002_invoice_uq'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. stock_snapshots table
    if 'stock_snapshots' not in tables:
        op.create_table(
            'stock_snapshots',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('balance', sa.Integer(), nullable=False),
            sa.Column('snapshot_date', sa.Date(), nullable=False),
            sa.Column('last_movement_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('company_id', 'product_id', 'snapshot_date', name='uq_stock_snapshot')
        )
        op.create_index('ix_stock_snapshots_id', 'stock_snapshots', ['id'], unique=False)
        op.create_index('ix_stock_snapshots_company_id', 'stock_snapshots', ['company_id'], unique=False)
        op.create_index('ix_stock_snapshots_product_id', 'stock_snapshots', ['product_id'], unique=False)

    # 2. bill_of_materials table
    if 'bill_of_materials' not in tables:
        op.create_table(
            'bill_of_materials',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('raw_material_id', sa.Integer(), sa.ForeignKey('raw_materials.id'), nullable=False),
            sa.Column('quantity_required', sa.Numeric(10, 4), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('company_id', 'product_id', 'raw_material_id', name='uq_bom_product_material')
        )
        op.create_index('ix_bill_of_materials_id', 'bill_of_materials', ['id'], unique=False)
        op.create_index('ix_bill_of_materials_company_id', 'bill_of_materials', ['company_id'], unique=False)
        op.create_index('ix_bill_of_materials_product_id', 'bill_of_materials', ['product_id'], unique=False)
        op.create_index('ix_bill_of_materials_raw_material_id', 'bill_of_materials', ['raw_material_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_bill_of_materials_raw_material_id', table_name='bill_of_materials')
    op.drop_index('ix_bill_of_materials_product_id', table_name='bill_of_materials')
    op.drop_index('ix_bill_of_materials_company_id', table_name='bill_of_materials')
    op.drop_index('ix_bill_of_materials_id', table_name='bill_of_materials')
    op.drop_table('bill_of_materials')

    op.drop_index('ix_stock_snapshots_product_id', table_name='stock_snapshots')
    op.drop_index('ix_stock_snapshots_company_id', table_name='stock_snapshots')
    op.drop_index('ix_stock_snapshots_id', table_name='stock_snapshots')
    op.drop_table('stock_snapshots')
