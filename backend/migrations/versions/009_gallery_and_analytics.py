"""009_gallery_and_analytics

Revision ID: 009_gallery_and_analytics
Revises: 008_hr_management
Create Date: 2026-09-29 22:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '009_gallery_and_analytics'
down_revision: Union[str, Sequence[str], None] = '008_hr_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Product Images Table
    if 'product_images' not in tables:
        op.create_table(
            'product_images',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('image_url', sa.String(length=512), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=False),
            sa.Column('mime_type', sa.String(length=64), server_default='image/jpeg', nullable=False),
            sa.Column('file_size_bytes', sa.Integer(), nullable=True),
            sa.Column('is_primary', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_product_images_id', 'product_images', ['id'], unique=False)
        op.create_index('ix_product_images_company_id', 'product_images', ['company_id'], unique=False)
        op.create_index('ix_product_images_product_id', 'product_images', ['product_id'], unique=False)

    # 2. Daily Factory Logs Table
    if 'daily_factory_logs' not in tables:
        op.create_table(
            'daily_factory_logs',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('date_ad', sa.String(length=10), nullable=False),
            sa.Column('date_bs', sa.String(length=10), nullable=False),
            sa.Column('total_workers', sa.Integer(), server_default='0', nullable=False),
            sa.Column('total_working_hours', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('total_pairs_produced', sa.Integer(), server_default='0', nullable=False),
            sa.Column('pairs_per_worker_ratio', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('pairs_per_man_hour_ratio', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('company_id', 'date_ad', name='uq_company_daily_log_date')
        )
        op.create_index('ix_daily_factory_logs_id', 'daily_factory_logs', ['id'], unique=False)
        op.create_index('ix_daily_factory_logs_company_id', 'daily_factory_logs', ['company_id'], unique=False)
        op.create_index('ix_daily_factory_logs_date_ad', 'daily_factory_logs', ['date_ad'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'daily_factory_logs' in tables:
        op.drop_table('daily_factory_logs')
    if 'product_images' in tables:
        op.drop_table('product_images')
