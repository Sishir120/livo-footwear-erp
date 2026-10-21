"""027_operational_numeric_precision

Revision ID: 027_operational_numeric_precision
Revises: 026_add_user_branch_id
Create Date: 2026-10-18 18:30:00.000000

Converts 33 operational financial, calculation, and inventory columns to standard,
precision-bounded SQL NUMERIC(p, s) types per the approved numeric contract:
- 14 Currency Columns to NUMERIC(14, 2) / NUMERIC(12, 2)
- 1 Raw Material Unit Rate Column to NUMERIC(14, 4)
- 1 Tax Rate Column to NUMERIC(5, 2)
- 4 Footwear Discrete Quantity Columns to NUMERIC(10, 2)
- 8 Raw Material & Waste Quantity Columns to NUMERIC(12, 4)
- 5 Labor Hours & Productivity Ratios to NUMERIC(8, 2) / NUMERIC(6, 2) / NUMERIC(8, 4)
Handles legacy floating-point defaults explicitly.
Preserves SQLite dynamic type affinity without table recreation.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '027_operational_numeric_precision'
down_revision: Union[str, Sequence[str], None] = '026_add_user_branch_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        # SQLite uses dynamic type affinity; no destructive table recreations needed.
        return

    # 1. clients (1 column)
    op.execute(sa.text("""
        ALTER TABLE clients
            ALTER COLUMN credit_limit TYPE NUMERIC(14, 2) USING ROUND(credit_limit::numeric, 2);
    """))

    # 2. daily_factory_logs (3 columns + defaults)
    op.execute(sa.text("""
        ALTER TABLE daily_factory_logs
            ALTER COLUMN total_working_hours TYPE NUMERIC(6, 2) USING ROUND(total_working_hours::numeric, 2),
            ALTER COLUMN total_working_hours SET DEFAULT 0.00,
            ALTER COLUMN pairs_per_worker_ratio TYPE NUMERIC(8, 4) USING ROUND(pairs_per_worker_ratio::numeric, 4),
            ALTER COLUMN pairs_per_worker_ratio SET DEFAULT 0.0000,
            ALTER COLUMN pairs_per_man_hour_ratio TYPE NUMERIC(8, 4) USING ROUND(pairs_per_man_hour_ratio::numeric, 4),
            ALTER COLUMN pairs_per_man_hour_ratio SET DEFAULT 0.0000;
    """))

    # 3. invoices (6 columns)
    op.execute(sa.text("""
        ALTER TABLE invoices
            ALTER COLUMN subtotal TYPE NUMERIC(14, 2) USING ROUND(subtotal::numeric, 2),
            ALTER COLUMN vat_rate TYPE NUMERIC(5, 2) USING ROUND(vat_rate::numeric, 2),
            ALTER COLUMN vat_amount TYPE NUMERIC(14, 2) USING ROUND(vat_amount::numeric, 2),
            ALTER COLUMN total_amount TYPE NUMERIC(14, 2) USING ROUND(total_amount::numeric, 2),
            ALTER COLUMN received_amount TYPE NUMERIC(14, 2) USING ROUND(received_amount::numeric, 2),
            ALTER COLUMN receivable_amount TYPE NUMERIC(14, 2) USING ROUND(receivable_amount::numeric, 2);
    """))

    # 4. payments (1 column)
    op.execute(sa.text("""
        ALTER TABLE payments
            ALTER COLUMN amount TYPE NUMERIC(14, 2) USING ROUND(amount::numeric, 2);
    """))

    # 5. production_batches (2 columns)
    op.execute(sa.text("""
        ALTER TABLE production_batches
            ALTER COLUMN target_quantity TYPE NUMERIC(10, 2) USING ROUND(target_quantity::numeric, 2),
            ALTER COLUMN produced_quantity TYPE NUMERIC(10, 2) USING ROUND(produced_quantity::numeric, 2);
    """))

    # 6. production_material_usage (1 column)
    op.execute(sa.text("""
        ALTER TABLE production_material_usage
            ALTER COLUMN quantity_used TYPE NUMERIC(12, 4) USING ROUND(quantity_used::numeric, 4);
    """))

    # 7. products (1 column)
    op.execute(sa.text("""
        ALTER TABLE products
            ALTER COLUMN unit_price TYPE NUMERIC(12, 2) USING ROUND(unit_price::numeric, 2);
    """))

    # 8. purchases (4 columns: 3 from 762ea2a34ccb + received_quantity)
    op.execute(sa.text("""
        ALTER TABLE purchases
            ALTER COLUMN quantity TYPE NUMERIC(12, 4) USING ROUND(quantity::numeric, 4),
            ALTER COLUMN unit_price TYPE NUMERIC(14, 4) USING ROUND(unit_price::numeric, 4),
            ALTER COLUMN total_amount TYPE NUMERIC(14, 2) USING ROUND(total_amount::numeric, 2),
            ALTER COLUMN received_quantity TYPE NUMERIC(12, 4) USING ROUND(received_quantity::numeric, 4),
            ALTER COLUMN received_quantity SET DEFAULT 0.0000;
    """))

    # 9. raw_materials (3 columns: min_stock_alert + current_stock + reorder_level)
    op.execute(sa.text("""
        ALTER TABLE raw_materials
            ALTER COLUMN min_stock_alert TYPE NUMERIC(12, 4) USING ROUND(min_stock_alert::numeric, 4),
            ALTER COLUMN current_stock TYPE NUMERIC(12, 4) USING ROUND(current_stock::numeric, 4),
            ALTER COLUMN current_stock SET DEFAULT 0.0000,
            ALTER COLUMN reorder_level TYPE NUMERIC(12, 4) USING ROUND(reorder_level::numeric, 4),
            ALTER COLUMN reorder_level SET DEFAULT 0.0000;
    """))

    # 10. sales_items (3 columns)
    op.execute(sa.text("""
        ALTER TABLE sales_items
            ALTER COLUMN quantity TYPE NUMERIC(10, 2) USING ROUND(quantity::numeric, 2),
            ALTER COLUMN unit_price TYPE NUMERIC(12, 2) USING ROUND(unit_price::numeric, 2),
            ALTER COLUMN total_price TYPE NUMERIC(14, 2) USING ROUND(total_price::numeric, 2);
    """))

    # 11. sales_orders (3 columns)
    op.execute(sa.text("""
        ALTER TABLE sales_orders
            ALTER COLUMN total_amount TYPE NUMERIC(14, 2) USING ROUND(total_amount::numeric, 2),
            ALTER COLUMN received_amount TYPE NUMERIC(14, 2) USING ROUND(received_amount::numeric, 2),
            ALTER COLUMN receivable_amount TYPE NUMERIC(14, 2) USING ROUND(receivable_amount::numeric, 2);
    """))

    # 12. stock_movements (1 column)
    op.execute(sa.text("""
        ALTER TABLE stock_movements
            ALTER COLUMN quantity TYPE NUMERIC(10, 2) USING ROUND(quantity::numeric, 2);
    """))

    # 13. worker_monthly_records (2 columns + defaults)
    op.execute(sa.text("""
        ALTER TABLE worker_monthly_records
            ALTER COLUMN total_working_hours TYPE NUMERIC(8, 2) USING ROUND(total_working_hours::numeric, 2),
            ALTER COLUMN total_working_hours SET DEFAULT 0.00,
            ALTER COLUMN overtime_hours TYPE NUMERIC(8, 2) USING ROUND(overtime_hours::numeric, 2),
            ALTER COLUMN overtime_hours SET DEFAULT 0.00;
    """))

    # 14. raw_material_movements (1 column)
    op.execute(sa.text("""
        ALTER TABLE raw_material_movements
            ALTER COLUMN quantity TYPE NUMERIC(12, 4) USING ROUND(quantity::numeric, 4);
    """))

    # 15. waste_records (1 column)
    op.execute(sa.text("""
        ALTER TABLE waste_records
            ALTER COLUMN quantity TYPE NUMERIC(12, 4) USING ROUND(quantity::numeric, 4);
    """))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        return

    # Revert 5 omitted columns back to double precision with original defaults
    op.execute(sa.text("""
        ALTER TABLE waste_records
            ALTER COLUMN quantity TYPE DOUBLE PRECISION USING quantity::double precision;

        ALTER TABLE raw_material_movements
            ALTER COLUMN quantity TYPE DOUBLE PRECISION USING quantity::double precision;

        ALTER TABLE purchases
            ALTER COLUMN received_quantity TYPE DOUBLE PRECISION USING received_quantity::double precision,
            ALTER COLUMN received_quantity SET DEFAULT '0'::double precision;

        ALTER TABLE raw_materials
            ALTER COLUMN current_stock TYPE DOUBLE PRECISION USING current_stock::double precision,
            ALTER COLUMN current_stock SET DEFAULT '0'::double precision,
            ALTER COLUMN reorder_level TYPE DOUBLE PRECISION USING reorder_level::double precision,
            ALTER COLUMN reorder_level SET DEFAULT '0'::double precision;
    """))

    # Revert 28 columns back to unconstrained numeric with original defaults
    op.execute(sa.text("""
        ALTER TABLE clients
            ALTER COLUMN credit_limit TYPE NUMERIC USING credit_limit::numeric;

        ALTER TABLE daily_factory_logs
            ALTER COLUMN total_working_hours TYPE NUMERIC USING total_working_hours::numeric,
            ALTER COLUMN total_working_hours SET DEFAULT '0'::double precision,
            ALTER COLUMN pairs_per_worker_ratio TYPE NUMERIC USING pairs_per_worker_ratio::numeric,
            ALTER COLUMN pairs_per_worker_ratio SET DEFAULT '0'::double precision,
            ALTER COLUMN pairs_per_man_hour_ratio TYPE NUMERIC USING pairs_per_man_hour_ratio::numeric,
            ALTER COLUMN pairs_per_man_hour_ratio SET DEFAULT '0'::double precision;

        ALTER TABLE invoices
            ALTER COLUMN subtotal TYPE NUMERIC USING subtotal::numeric,
            ALTER COLUMN vat_rate TYPE NUMERIC USING vat_rate::numeric,
            ALTER COLUMN vat_amount TYPE NUMERIC USING vat_amount::numeric,
            ALTER COLUMN total_amount TYPE NUMERIC USING total_amount::numeric,
            ALTER COLUMN received_amount TYPE NUMERIC USING received_amount::numeric,
            ALTER COLUMN receivable_amount TYPE NUMERIC USING receivable_amount::numeric;

        ALTER TABLE payments
            ALTER COLUMN amount TYPE NUMERIC USING amount::numeric;

        ALTER TABLE production_batches
            ALTER COLUMN target_quantity TYPE NUMERIC USING target_quantity::numeric,
            ALTER COLUMN produced_quantity TYPE NUMERIC USING produced_quantity::numeric;

        ALTER TABLE production_material_usage
            ALTER COLUMN quantity_used TYPE NUMERIC USING quantity_used::numeric;

        ALTER TABLE products
            ALTER COLUMN unit_price TYPE NUMERIC USING unit_price::numeric;

        ALTER TABLE purchases
            ALTER COLUMN quantity TYPE NUMERIC USING quantity::numeric,
            ALTER COLUMN unit_price TYPE NUMERIC USING unit_price::numeric,
            ALTER COLUMN total_amount TYPE NUMERIC USING total_amount::numeric;

        ALTER TABLE raw_materials
            ALTER COLUMN min_stock_alert TYPE NUMERIC USING min_stock_alert::numeric;

        ALTER TABLE sales_items
            ALTER COLUMN quantity TYPE NUMERIC USING quantity::numeric,
            ALTER COLUMN unit_price TYPE NUMERIC USING unit_price::numeric,
            ALTER COLUMN total_price TYPE NUMERIC USING total_price::numeric;

        ALTER TABLE sales_orders
            ALTER COLUMN total_amount TYPE NUMERIC USING total_amount::numeric,
            ALTER COLUMN received_amount TYPE NUMERIC USING received_amount::numeric,
            ALTER COLUMN receivable_amount TYPE NUMERIC USING receivable_amount::numeric;

        ALTER TABLE stock_movements
            ALTER COLUMN quantity TYPE NUMERIC USING quantity::numeric;

        ALTER TABLE worker_monthly_records
            ALTER COLUMN total_working_hours TYPE NUMERIC USING total_working_hours::numeric,
            ALTER COLUMN total_working_hours SET DEFAULT '0'::double precision,
            ALTER COLUMN overtime_hours TYPE NUMERIC USING overtime_hours::numeric,
            ALTER COLUMN overtime_hours SET DEFAULT '0'::double precision;
    """))
