"""029_add_pan_number_to_parties

Revision ID: 029_add_pan_number_to_parties
Revises: 028_register_double_entry_accounting_ledger
Create Date: 2026-10-20 20:30:00.000000

Adds statutory pan_number column to clients and suppliers tables.
Enables B2B VAT compliance under Nepal Value Added Tax Act 2052,
populating Permanent Account Numbers into Annex-5 (Sales Book)
and Annex-8 (Purchase Book) statutory tax registers.
Preserves existing records with nullable values.
Supports both PostgreSQL and SQLite via batch operations.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '029_add_pan_number_to_parties'
down_revision: Union[str, Sequence[str], None] = '028_register_double_entry_accounting_ledger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # 1. Add pan_number to clients
    if 'clients' in tables:
        columns = {c['name'] for c in inspector.get_columns('clients')}
        if 'pan_number' not in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('clients') as batch_op:
                    batch_op.add_column(sa.Column('pan_number', sa.String(15), nullable=True))
            else:
                op.add_column('clients', sa.Column('pan_number', sa.String(15), nullable=True))

    # 2. Add pan_number to suppliers
    if 'suppliers' in tables:
        columns = {c['name'] for c in inspector.get_columns('suppliers')}
        if 'pan_number' not in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('suppliers') as batch_op:
                    batch_op.add_column(sa.Column('pan_number', sa.String(15), nullable=True))
            else:
                op.add_column('suppliers', sa.Column('pan_number', sa.String(15), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # 1. Drop pan_number from clients
    if 'clients' in tables:
        columns = {c['name'] for c in inspector.get_columns('clients')}
        if 'pan_number' in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('clients') as batch_op:
                    batch_op.drop_column('pan_number')
            else:
                op.drop_column('clients', 'pan_number')

    # 2. Drop pan_number from suppliers
    if 'suppliers' in tables:
        columns = {c['name'] for c in inspector.get_columns('suppliers')}
        if 'pan_number' in columns:
            if conn.dialect.name == 'sqlite':
                with op.batch_alter_table('suppliers') as batch_op:
                    batch_op.drop_column('pan_number')
            else:
                op.drop_column('suppliers', 'pan_number')
