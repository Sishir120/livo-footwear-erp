"""014_raw_material_ledger_and_landed_cost

Revision ID: 014_raw_material_ledger_and_landed_cost
Revises: 013_merge_heads
Create Date: 2026-10-11 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '014_raw_material_ledger_and_landed_cost'
down_revision: Union[str, Sequence[str], None] = '013_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)

    # 1. Create raw_material_movements table if not exists
    tables = set(inspector.get_table_names())
    if 'raw_material_movements' not in tables:
        op.create_table(
            'raw_material_movements',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('raw_material_id', sa.Integer(), sa.ForeignKey('raw_materials.id'), nullable=False, index=True),
            sa.Column('movement_date', sa.Date(), nullable=False),
            sa.Column('movement_date_bs', sa.String(length=10), nullable=False),
            sa.Column('direction', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('unit_cost_paisa', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('movement_type', sa.String(length=32), nullable=False),
            sa.Column('reference_voucher', sa.String(length=64), nullable=False),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("direction IN (1, -1)", name="chk_rm_movement_direction"),
            sa.CheckConstraint("quantity > 0", name="chk_rm_movement_quantity_positive")
        )
        op.create_index(
            'ix_rm_movements_company_material_date',
            'raw_material_movements',
            ['company_id', 'raw_material_id', 'movement_date']
        )

    # 2. Add landed cost and receiving columns to purchases
    purchases_cols = {c['name'] for c in inspector.get_columns('purchases')}
    new_cols = [
        ('carrying_in_paisa', sa.BigInteger(), '0', False),
        ('import_duty_paisa', sa.BigInteger(), '0', False),
        ('china_carrying_paisa', sa.BigInteger(), '0', False),
        ('insurance_paisa', sa.BigInteger(), '0', False),
        ('total_landed_cost_paisa', sa.BigInteger(), '0', False),
        ('effective_unit_rate_paisa', sa.BigInteger(), '0', False),
        ('received_quantity', sa.Float(), '0.0', False),
    ]

    for col_name, col_type, s_default, is_null in new_cols:
        if col_name not in purchases_cols:
            op.add_column('purchases', sa.Column(col_name, col_type, server_default=s_default, nullable=is_null))

    if 'grn_number' not in purchases_cols:
        op.add_column('purchases', sa.Column('grn_number', sa.String(length=32), nullable=True))
        op.create_index('uq_purchases_grn_number', 'purchases', ['grn_number'], unique=True)

    if 'received_by_id' not in purchases_cols:
        if conn.dialect.name == 'sqlite':
            op.add_column('purchases', sa.Column('received_by_id', sa.Integer(), nullable=True))
        else:
            op.add_column('purchases', sa.Column('received_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    inspector = inspect(conn)

    indexes = {i['name'] for i in inspector.get_indexes('purchases')}
    if 'uq_purchases_grn_number' in indexes:
        op.drop_index('uq_purchases_grn_number', table_name='purchases')

    purchases_cols = {c['name'] for c in inspector.get_columns('purchases')}
    cols_to_drop = [
        'carrying_in_paisa',
        'import_duty_paisa',
        'china_carrying_paisa',
        'insurance_paisa',
        'total_landed_cost_paisa',
        'effective_unit_rate_paisa',
        'received_quantity',
        'grn_number',
        'received_by_id'
    ]

    for col in cols_to_drop:
        if col in purchases_cols:
            op.drop_column('purchases', col)

    tables = set(inspector.get_table_names())
    if 'raw_material_movements' in tables:
        op.drop_table('raw_material_movements')
