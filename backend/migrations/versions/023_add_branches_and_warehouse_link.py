"""023_add_branches_and_warehouse_link

Revision ID: 023_add_branches_and_warehouse_link
Revises: 022_add_stock_transfers
Create Date: 2026-10-15 14:00:00.000000

Adds branches table for operating location management and links warehouses to branches.
Preserves existing warehouses with nullable branch_id.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '023_add_branches_and_warehouse_link'
down_revision: Union[str, Sequence[str], None] = '022_add_stock_transfers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'branches' not in tables:
        op.create_table(
            'branches',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('code', sa.String(length=50), nullable=False, index=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('type', sa.String(length=30), nullable=False, server_default='RETAIL_OUTLET'),
            sa.Column('address', sa.String(length=255), nullable=True),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('email', sa.String(length=100), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('company_id', 'code', name='uq_company_branch_code')
        )
        op.create_index('ix_branches_company_code', 'branches', ['company_id', 'code'])

    # Check warehouses table for branch_id column
    if 'warehouses' in tables:
        columns = {c['name'] for c in inspector.get_columns('warehouses')}
        if 'branch_id' not in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('warehouses') as batch_op:
                    batch_op.add_column(sa.Column('branch_id', sa.Integer(), nullable=True))
                    batch_op.create_foreign_key('fk_warehouses_branch_id', 'branches', ['branch_id'], ['id'])
                    batch_op.create_index('ix_warehouses_branch_id', ['branch_id'])
            else:
                op.add_column('warehouses', sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id', name='fk_warehouses_branch_id'), nullable=True))
                op.create_index('ix_warehouses_branch_id', 'warehouses', ['branch_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'warehouses' in tables:
        columns = {c['name'] for c in inspector.get_columns('warehouses')}
        if 'branch_id' in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('warehouses') as batch_op:
                    batch_op.drop_constraint('fk_warehouses_branch_id', type_='foreignkey')
                    batch_op.drop_index('ix_warehouses_branch_id')
                    batch_op.drop_column('branch_id')
            else:
                op.drop_index('ix_warehouses_branch_id', table_name='warehouses')
                op.drop_constraint('fk_warehouses_branch_id', table_name='warehouses', type_='foreignkey')
                op.drop_column('warehouses', 'branch_id')

    if 'branches' in tables:
        op.drop_table('branches')
