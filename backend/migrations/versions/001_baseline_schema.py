"""001_baseline_schema

Revision ID: 001_baseline
Revises: 
Create Date: 2026-09-26 08:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. companies
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('pan_number', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_company_id'), 'users', ['company_id'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 3. audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('target_table', sa.String(length=100), nullable=True),
        sa.Column('record_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_company_id'), 'audit_log', ['company_id'], unique=False)
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)

    # 4. suppliers
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppliers_code'), 'suppliers', ['code'], unique=False)
    op.create_index(op.f('ix_suppliers_company_id'), 'suppliers', ['company_id'], unique=False)
    op.create_index(op.f('ix_suppliers_id'), 'suppliers', ['id'], unique=False)

    # 5. raw_materials
    op.create_table(
        'raw_materials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('min_stock_alert', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raw_materials_code'), 'raw_materials', ['code'], unique=False)
    op.create_index(op.f('ix_raw_materials_company_id'), 'raw_materials', ['company_id'], unique=False)
    op.create_index(op.f('ix_raw_materials_id'), 'raw_materials', ['id'], unique=False)

    # 6. purchases
    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('raw_material_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('purchase_date_ad', sa.String(length=10), nullable=False),
        sa.Column('purchase_date_bs', sa.String(length=10), nullable=False),
        sa.Column('payment_status', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['raw_material_id'], ['raw_materials.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchases_company_id'), 'purchases', ['company_id'], unique=False)
    op.create_index(op.f('ix_purchases_id'), 'purchases', ['id'], unique=False)
    op.create_index(op.f('ix_purchases_purchase_date_ad'), 'purchases', ['purchase_date_ad'], unique=False)
    op.create_index(op.f('ix_purchases_raw_material_id'), 'purchases', ['raw_material_id'], unique=False)
    op.create_index(op.f('ix_purchases_supplier_id'), 'purchases', ['supplier_id'], unique=False)

    # 7. products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_code'), 'products', ['code'], unique=False)
    op.create_index(op.f('ix_products_company_id'), 'products', ['company_id'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)

    # 8. stock_movements
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('direction', sa.Integer(), nullable=False),
        sa.Column('ref_type', sa.String(length=50), nullable=False),
        sa.Column('ref_id', sa.Integer(), nullable=True),
        sa.Column('date_ad', sa.String(length=10), nullable=False),
        sa.Column('date_bs', sa.String(length=10), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_movements_company_id'), 'stock_movements', ['company_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_date_ad'), 'stock_movements', ['date_ad'], unique=False)
    op.create_index(op.f('ix_stock_movements_id'), 'stock_movements', ['id'], unique=False)
    op.create_index(op.f('ix_stock_movements_product_id'), 'stock_movements', ['product_id'], unique=False)

    # 9. production_batches
    op.create_table(
        'production_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(length=50), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('target_quantity', sa.Float(), nullable=False),
        sa.Column('produced_quantity', sa.Float(), nullable=False),
        sa.Column('worker_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('date_ad', sa.String(length=10), nullable=False),
        sa.Column('date_bs', sa.String(length=10), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_batches_batch_number'), 'production_batches', ['batch_number'], unique=False)
    op.create_index(op.f('ix_production_batches_company_id'), 'production_batches', ['company_id'], unique=False)
    op.create_index(op.f('ix_production_batches_date_ad'), 'production_batches', ['date_ad'], unique=False)
    op.create_index(op.f('ix_production_batches_id'), 'production_batches', ['id'], unique=False)
    op.create_index(op.f('ix_production_batches_product_id'), 'production_batches', ['product_id'], unique=False)

    # 10. production_material_usage
    op.create_table(
        'production_material_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('raw_material_id', sa.Integer(), nullable=False),
        sa.Column('quantity_used', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['production_batches.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['raw_material_id'], ['raw_materials.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_material_usage_batch_id'), 'production_material_usage', ['batch_id'], unique=False)
    op.create_index(op.f('ix_production_material_usage_company_id'), 'production_material_usage', ['company_id'], unique=False)
    op.create_index(op.f('ix_production_material_usage_id'), 'production_material_usage', ['id'], unique=False)

    # 11. clients
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('credit_limit', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_code'), 'clients', ['code'], unique=False)
    op.create_index(op.f('ix_clients_company_id'), 'clients', ['company_id'], unique=False)
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)

    # 12. sales_orders
    op.create_table(
        'sales_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('order_date_ad', sa.String(length=10), nullable=False),
        sa.Column('order_date_bs', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('received_amount', sa.Float(), nullable=False),
        sa.Column('receivable_amount', sa.Float(), nullable=False),
        sa.Column('delivered', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_orders_client_id'), 'sales_orders', ['client_id'], unique=False)
    op.create_index(op.f('ix_sales_orders_company_id'), 'sales_orders', ['company_id'], unique=False)
    op.create_index(op.f('ix_sales_orders_id'), 'sales_orders', ['id'], unique=False)
    op.create_index(op.f('ix_sales_orders_order_date_ad'), 'sales_orders', ['order_date_ad'], unique=False)
    op.create_index(op.f('ix_sales_orders_order_number'), 'sales_orders', ['order_number'], unique=False)

    # 13. sales_items
    op.create_table(
        'sales_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('sales_order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('total_price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_items_company_id'), 'sales_items', ['company_id'], unique=False)
    op.create_index(op.f('ix_sales_items_id'), 'sales_items', ['id'], unique=False)
    op.create_index(op.f('ix_sales_items_product_id'), 'sales_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_sales_items_sales_order_id'), 'sales_items', ['sales_order_id'], unique=False)

    # 14. payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('sales_order_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payment_date_ad', sa.String(length=10), nullable=False),
        sa.Column('payment_date_bs', sa.String(length=10), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_client_id'), 'payments', ['client_id'], unique=False)
    op.create_index(op.f('ix_payments_company_id'), 'payments', ['company_id'], unique=False)
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_payment_date_ad'), 'payments', ['payment_date_ad'], unique=False)
    op.create_index(op.f('ix_payments_sales_order_id'), 'payments', ['sales_order_id'], unique=False)

    # 15. invoices (Baseline schema without unique constraint yet)
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('sales_order_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('date_ad', sa.String(length=10), nullable=False),
        sa.Column('date_bs', sa.String(length=10), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.Column('vat_enabled', sa.Boolean(), nullable=False),
        sa.Column('vat_rate', sa.Float(), nullable=False),
        sa.Column('vat_amount', sa.Float(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('received_amount', sa.Float(), nullable=False),
        sa.Column('receivable_amount', sa.Float(), nullable=False),
        sa.Column('is_void', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_company_id'), 'invoices', ['company_id'], unique=False)
    op.create_index(op.f('ix_invoices_date_ad'), 'invoices', ['date_ad'], unique=False)
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_invoices_sales_order_id'), 'invoices', ['sales_order_id'], unique=False)
    op.create_index(op.f('ix_invoices_sequence_number'), 'invoices', ['sequence_number'], unique=False)

def downgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('payments')
    op.drop_table('sales_items')
    op.drop_table('sales_orders')
    op.drop_table('clients')
    op.drop_table('production_material_usage')
    op.drop_table('production_batches')
    op.drop_table('stock_movements')
    op.drop_table('products')
    op.drop_table('purchases')
    op.drop_table('raw_materials')
    op.drop_table('suppliers')
    op.drop_table('audit_log')
    op.drop_table('users')
    op.drop_table('companies')
