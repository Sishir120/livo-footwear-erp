"""016_production_batch_color_and_gallery_link

Phase 4A: Production batch color and gallery image association.
Adds nullable color to production_batches.
Adds nullable production_batch_id with foreign key (SET NULL) and indexes to product_images.

Revision ID: 016_production_batch_color_and_gallery_link
Revises: 015_sales_dispatch_and_expenses
Create Date: 2026-10-12 09:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '016_production_batch_color_and_gallery_link'
down_revision: Union[str, Sequence[str], None] = '015_sales_dispatch_and_expenses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # 1. Add color to production_batches
    batch_cols = {c['name'] for c in inspector.get_columns('production_batches')}
    if 'color' not in batch_cols:
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('production_batches') as batch_op:
                batch_op.add_column(sa.Column('color', sa.String(length=50), nullable=True))
        else:
            op.add_column('production_batches', sa.Column('color', sa.String(length=50), nullable=True))

    # 2. Add production_batch_id and indexes to product_images
    img_cols = {c['name'] for c in inspector.get_columns('product_images')}
    img_indexes = {idx['name'] for idx in inspector.get_indexes('product_images')}

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('product_images') as batch_op:
            if 'production_batch_id' not in img_cols:
                batch_op.add_column(sa.Column('production_batch_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_product_images_production_batch_id',
                    'production_batches',
                    ['production_batch_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            if 'ix_product_images_production_batch_id' not in img_indexes:
                batch_op.create_index('ix_product_images_production_batch_id', ['production_batch_id'], unique=False)
            if 'ix_product_images_company_batch' not in img_indexes:
                batch_op.create_index('ix_product_images_company_batch', ['company_id', 'production_batch_id'], unique=False)
    else:
        if 'production_batch_id' not in img_cols:
            op.add_column(
                'product_images',
                sa.Column(
                    'production_batch_id',
                    sa.Integer(),
                    sa.ForeignKey('production_batches.id', ondelete='SET NULL'),
                    nullable=True
                )
            )
        if 'ix_product_images_production_batch_id' not in img_indexes:
            op.create_index('ix_product_images_production_batch_id', 'product_images', ['production_batch_id'], unique=False)
        if 'ix_product_images_company_batch' not in img_indexes:
            op.create_index('ix_product_images_company_batch', 'product_images', ['company_id', 'production_batch_id'], unique=False)


def downgrade() -> None:
    """
    WARNING / DATA SAFETY LIMITATION:
    Downgrading drops the 'color' column from production_batches and the 'production_batch_id'
    column from product_images. Any custom batch color data or batch-to-image associations
    created during Phase 4A will be permanently removed.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # 1. Drop production_batch_id and indexes from product_images
    img_cols = {c['name'] for c in inspector.get_columns('product_images')}
    img_indexes = {idx['name'] for idx in inspector.get_indexes('product_images')}

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('product_images') as batch_op:
            if 'ix_product_images_company_batch' in img_indexes:
                batch_op.drop_index('ix_product_images_company_batch')
            if 'ix_product_images_production_batch_id' in img_indexes:
                batch_op.drop_index('ix_product_images_production_batch_id')
            if 'production_batch_id' in img_cols:
                batch_op.drop_column('production_batch_id')
    else:
        if 'ix_product_images_company_batch' in img_indexes:
            op.drop_index('ix_product_images_company_batch', table_name='product_images')
        if 'ix_product_images_production_batch_id' in img_indexes:
            op.drop_index('ix_product_images_production_batch_id', table_name='product_images')
        if 'production_batch_id' in img_cols:
            op.drop_column('product_images', 'production_batch_id')

    # 2. Drop color from production_batches
    batch_cols = {c['name'] for c in inspector.get_columns('production_batches')}
    if 'color' in batch_cols:
        if conn.dialect.name == 'sqlite':
            with op.batch_alter_table('production_batches') as batch_op:
                batch_op.drop_column('color')
        else:
            op.drop_column('production_batches', 'color')
