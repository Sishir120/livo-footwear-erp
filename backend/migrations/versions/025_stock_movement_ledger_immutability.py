"""025_stock_movement_ledger_immutability

Revision ID: 025_stock_movement_ledger_immutability
Revises: 024_add_rate_limit_entries
Create Date: 2026-10-17 12:00:00.000000

Adds database-level triggers to enforce append-only immutability on stock_movements.
Direct UPDATE and DELETE operations are prohibited at the database engine level.
Corrections must use compensating VOID_REVERSAL or ADJUSTMENT transactions.
"""
from typing import Sequence, Union
from alembic import op


revision: str = '025_stock_movement_ledger_immutability'
down_revision: Union[str, Sequence[str], None] = '024_add_rate_limit_entries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_stock_movement_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'StockMovement ledger rows are immutable. Updates and deletes are prohibited. Use compensating VOID_REVERSAL or ADJUSTMENT transactions instead.';
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            DROP TRIGGER IF EXISTS trg_stock_movement_immutable ON stock_movements;
            CREATE TRIGGER trg_stock_movement_immutable
            BEFORE UPDATE OR DELETE ON stock_movements
            FOR EACH ROW
            EXECUTE FUNCTION prevent_stock_movement_modification();
        """)
    elif dialect == "sqlite":
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_stock_movement_no_update
            BEFORE UPDATE ON stock_movements
            BEGIN
                SELECT RAISE(ABORT, 'StockMovement ledger rows are immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_stock_movement_no_delete
            BEFORE DELETE ON stock_movements
            BEGIN
                SELECT RAISE(ABORT, 'StockMovement ledger rows are immutable');
            END;
        """)


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_stock_movement_immutable ON stock_movements;")
        op.execute("DROP FUNCTION IF EXISTS prevent_stock_movement_modification();")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_stock_movement_no_update;")
        op.execute("DROP TRIGGER IF EXISTS trg_stock_movement_no_delete;")
