"""021_add_document_sequences

Revision ID: 021_add_document_sequences
Revises: 020_fixed_assets_waste_and_expenses
Create Date: 2026-10-15 11:30:00.000000

Adds document_sequences table for collision-resistant sequence generation.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = '021_add_document_sequences'
down_revision: Union[str, Sequence[str], None] = '020_fixed_assets_waste_and_expenses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'document_sequences' not in tables:
        op.create_table(
            'document_sequences',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('document_type', sa.String(length=50), nullable=False, index=True),
            sa.Column('current_sequence', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('company_id', 'document_type', name='uq_company_doc_type_sequence')
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'document_sequences' in tables:
        op.drop_table('document_sequences')
