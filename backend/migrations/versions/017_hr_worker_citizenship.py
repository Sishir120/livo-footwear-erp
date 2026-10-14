"""017_hr_worker_citizenship

Phase 4B: Worker citizenship document management and sensitive identity storage.
Adds nullable citizenship_doc_path, citizenship_doc_name, and citizenship_uploaded_at to workers.

Revision ID: 017_hr_worker_citizenship
Revises: 016_production_batch_color_and_gallery_link
Create Date: 2026-10-12 11:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '017_hr_worker_citizenship'
down_revision: Union[str, Sequence[str], None] = '016_production_batch_color_and_gallery_link'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    workers_cols = {c['name'] for c in inspector.get_columns('workers')}

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('workers') as batch_op:
            if 'citizenship_doc_path' not in workers_cols:
                batch_op.add_column(sa.Column('citizenship_doc_path', sa.String(length=512), nullable=True))
            if 'citizenship_doc_name' not in workers_cols:
                batch_op.add_column(sa.Column('citizenship_doc_name', sa.String(length=255), nullable=True))
            if 'citizenship_uploaded_at' not in workers_cols:
                batch_op.add_column(sa.Column('citizenship_uploaded_at', sa.DateTime(timezone=True), nullable=True))
    else:
        if 'citizenship_doc_path' not in workers_cols:
            op.add_column('workers', sa.Column('citizenship_doc_path', sa.String(length=512), nullable=True))
        if 'citizenship_doc_name' not in workers_cols:
            op.add_column('workers', sa.Column('citizenship_doc_name', sa.String(length=255), nullable=True))
        if 'citizenship_uploaded_at' not in workers_cols:
            op.add_column('workers', sa.Column('citizenship_uploaded_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    workers_cols = {c['name'] for c in inspector.get_columns('workers')}

    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('workers') as batch_op:
            if 'citizenship_uploaded_at' in workers_cols:
                batch_op.drop_column('citizenship_uploaded_at')
            if 'citizenship_doc_name' in workers_cols:
                batch_op.drop_column('citizenship_doc_name')
            if 'citizenship_doc_path' in workers_cols:
                batch_op.drop_column('citizenship_doc_path')
    else:
        if 'citizenship_uploaded_at' in workers_cols:
            op.drop_column('workers', 'citizenship_uploaded_at')
        if 'citizenship_doc_name' in workers_cols:
            op.drop_column('workers', 'citizenship_doc_name')
        if 'citizenship_doc_path' in workers_cols:
            op.drop_column('workers', 'citizenship_doc_path')
