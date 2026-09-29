"""005_stock_card_ledger

Revision ID: 005_stock_card_ledger
Revises: 004_invoice_sequences
Create Date: 2026-09-29 08:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_stock_card_ledger'
down_revision: Union[str, Sequence[str], None] = '004_invoice_sequences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create warehouses table if not exists
    if 'warehouses' not in tables:
        op.create_table(
            'warehouses',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_warehouses_id', 'warehouses', ['id'], unique=False)
        op.create_index('ix_warehouses_company_id', 'warehouses', ['company_id'], unique=False)
        op.create_index('ix_warehouses_code', 'warehouses', ['code'], unique=False)

    # 2. Seed default warehouse (id=1) for company 1 if available
    existing_wh = conn.execute(sa.text("SELECT id FROM warehouses WHERE id = 1")).fetchone()
    if not existing_wh:
        has_comp = conn.execute(sa.text("SELECT id FROM companies WHERE id = 1")).fetchone()
        if has_comp:
            conn.execute(
                sa.text(
                    "INSERT INTO warehouses (id, company_id, name, code, location, is_active, created_at) "
                    "VALUES (1, 1, 'Main Finished Warehouse (केन्द्रीय गोदाम)', 'WH-01', 'Kathmandu Factory Floor', :active, CURRENT_TIMESTAMP)"
                ),
                {"active": True}
            )

    # 3. Add audit and stock card columns to stock_movements if missing
    existing_cols = {c['name'] for c in inspector.get_columns('stock_movements')}
    existing_indices = {ix['name'] for ix in inspector.get_indexes('stock_movements')}

    with op.batch_alter_table('stock_movements') as batch_op:
        if 'warehouse_id' not in existing_cols:
            batch_op.add_column(sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id', name='fk_stock_movements_warehouse'), nullable=False, server_default='1'))
        if 'size' not in existing_cols:
            batch_op.add_column(sa.Column('size', sa.String(length=20), nullable=True))
        if 'movement_type' not in existing_cols:
            batch_op.add_column(sa.Column('movement_type', sa.String(length=50), nullable=False, server_default='PRODUCTION_IN'))
        if 'source_doc_ref' not in existing_cols:
            batch_op.add_column(sa.Column('source_doc_ref', sa.String(length=64), nullable=True))
        if 'reversal_of_id' not in existing_cols:
            batch_op.add_column(sa.Column('reversal_of_id', sa.Integer(), sa.ForeignKey('stock_movements.id', name='fk_stock_movements_reversal_of'), nullable=True))
        if 'reason_code' not in existing_cols:
            batch_op.add_column(sa.Column('reason_code', sa.String(length=32), nullable=True))
        if 'reason_text' not in existing_cols:
            batch_op.add_column(sa.Column('reason_text', sa.String(length=255), nullable=True))
        if 'actor_id' not in existing_cols:
            batch_op.add_column(sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_stock_movements_actor'), nullable=False, server_default='1'))
        if 'approved_by_id' not in existing_cols:
            batch_op.add_column(sa.Column('approved_by_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_stock_movements_approved_by'), nullable=True))
        if 'ix_stock_ledger_lookup' not in existing_indices:
            batch_op.create_index('ix_stock_ledger_lookup', ['company_id', 'product_id', 'size', 'created_at'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.drop_index('ix_stock_ledger_lookup')
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('actor_id')
        batch_op.drop_column('reason_text')
        batch_op.drop_column('reason_code')
        batch_op.drop_column('reversal_of_id')
        batch_op.drop_column('source_doc_ref')
        batch_op.drop_column('movement_type')
        batch_op.drop_column('size')
        batch_op.drop_column('warehouse_id')

    op.drop_table('warehouses')
