# Day 2.2 Endpoint Authorization Inventory & Matrix

**Total Registered Routes:** 141  
**Generated:** 2026-10-16  
**Methodology:** Extracted dynamically from live FastAPI `app.routes` route registry and dependency graph.

| Method | Effective Path | Authentication | Required Role | Tenant Isolation | Branch/Warehouse Scope | Sensitive Data Handled |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/openapi.json` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/docs` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/docs/oauth2-redirect` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/redoc` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/health` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/health/live` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/health/ready` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/diagnostics/download` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `GET` | `/api/v1/health` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/api/v1/health/live` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/api/v1/health/ready` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/api/v1/diagnostics/download` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `GET` | `/api/v1/metrics` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/api/v1/metrics/json` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `POST` | `/api/v1/auth/login` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `POST` | `/api/v1/auth/logout` | Public / Anonymous | `None` | N/A (Public) | N/A | General / Operational |
| `GET` | `/api/v1/auth/me` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/auth/users` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | Credentials / Roles |
| `POST` | `/api/v1/auth/users` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | Credentials / Roles |
| `PATCH` | `/api/v1/auth/users/{user_id}` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | Credentials / Roles |
| `GET` | `/api/v1/purchase/suppliers` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/suppliers` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/suppliers/{supplier_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/raw-materials` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/raw-materials` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/raw-materials/{material_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `PATCH` | `/api/v1/purchase/raw-materials/{material_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/purchases` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/purchases/{purchase_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/purchases` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/purchases/{purchase_id}/receive` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/raw-materials/{material_id}/card` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchase/materials/{material_id}/card` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/raw-materials/{material_id}/adjust` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchase/materials/{material_id}/adjust` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchases/` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchases` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchases/{purchase_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchases/` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchases` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchases/{purchase_id}/receive` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchases/raw-materials/{material_id}/card` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/purchases/materials/{material_id}/card` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchases/raw-materials/{material_id}/adjust` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/purchases/materials/{material_id}/adjust` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/production/products` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `POST` | `/api/v1/production/products` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `GET` | `/api/v1/production/products/{product_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `GET` | `/api/v1/production/bom` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `POST` | `/api/v1/production/bom` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `DELETE` | `/api/v1/production/bom/{bom_id}` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `GET` | `/api/v1/production/batches` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `GET` | `/api/v1/production/batches/{batch_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `POST` | `/api/v1/production/batches` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `POST` | `/api/v1/production/sync/draft` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `GET` | `/api/v1/stock/movements` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/stock/movements` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/snapshots` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/stock/snapshots` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/balance` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/warehouses` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/warehouses/{warehouse_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/ledger` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/stock/adjustments` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `POST` | `/api/v1/stock/reversals/{movement_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/stock/curve/{product_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/sales/clients` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/sales/clients` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/sales/clients/{client_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/sales/orders` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/sales/orders/{order_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/sales/orders` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/sales/orders/{order_id}/dispatch` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/sales/payments` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/sales/expenses` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/sales/expenses` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `DELETE` | `/api/v1/sales/expenses/{expense_id}` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/invoices` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/invoices` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `PATCH` | `/api/v1/invoices/{invoice_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/invoices/{invoice_id}/finalize` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/invoices/{invoice_id}/credit-note` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/invoices/{invoice_id}/cancel` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/invoices/{invoice_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/invoices/{invoice_id}/printable` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/reports/daily` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/reports/stock` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Warehouse validated in company | Inventory / Valuation |
| `GET` | `/api/v1/backup/status` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `GET` | `/api/v1/backup/health` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `POST` | `/api/v1/backup/run` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `GET` | `/api/v1/receivables/aging` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/receivables/statement/{client_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/receivables/payments` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `POST` | `/api/v1/receivables/dispute/{entry_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/receivables/invoices/{client_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Financial / Invoices / Payments |
| `GET` | `/api/v1/ops/telemetry` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | System Telemetry / Database Dump |
| `GET` | `/api/v1/hr/workers` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/hr/workers` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `PATCH` | `/api/v1/hr/workers/{worker_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `PATCH` | `/api/v1/hr/workers/{worker_id}/status` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/hr/advances` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `GET` | `/api/v1/hr/workers/{worker_id}/history` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/hr/monthly-payroll` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `GET` | `/api/v1/hr/settings` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `PUT` | `/api/v1/hr/settings` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/hr/workers/{worker_id}/photo` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `GET` | `/api/v1/hr/workers/{worker_id}/photo` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `DELETE` | `/api/v1/hr/workers/{worker_id}/photo` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/hr/workers/{worker_id}/citizenship` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `GET` | `/api/v1/hr/workers/{worker_id}/citizenship` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `DELETE` | `/api/v1/hr/workers/{worker_id}/citizenship` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | HR / PII / Payroll |
| `POST` | `/api/v1/gallery/upload/{product_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/gallery` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/gallery/images/{image_id}/download` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `DELETE` | `/api/v1/gallery/{image_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/analytics/top-products` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/analytics/top-customers` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/analytics/production-ratios` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | Inventory / Valuation |
| `POST` | `/api/v1/analytics/daily-logs` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/fixed-assets` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `POST` | `/api/v1/fixed-assets` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `DELETE` | `/api/v1/fixed-assets/{asset_id}` | Authenticated (Cookie/JWT) | `admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/waste` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `POST` | `/api/v1/waste` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `DELETE` | `/api/v1/waste/{record_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/expenses/factory` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `POST` | `/api/v1/expenses/factory` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `DELETE` | `/api/v1/expenses/factory/{expense_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | N/A | General / Operational |
| `GET` | `/api/v1/transfers` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `POST` | `/api/v1/transfers` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `GET` | `/api/v1/transfers/{transfer_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `POST` | `/api/v1/transfers/{transfer_id}/dispatch` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `POST` | `/api/v1/transfers/{transfer_id}/receive` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `POST` | `/api/v1/transfers/{transfer_id}/cancel` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Source & destination warehouses validated in company | Inventory / Valuation |
| `GET` | `/api/v1/branches` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `POST` | `/api/v1/branches` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `GET` | `/api/v1/branches/{branch_id}` | Authenticated (Cookie/JWT) | `viewer, editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `PUT` | `/api/v1/branches/{branch_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `PATCH` | `/api/v1/branches/{branch_id}/toggle-active` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `POST` | `/api/v1/branches/{branch_id}/warehouses` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
| `DELETE` | `/api/v1/branches/{branch_id}/warehouses/{warehouse_id}` | Authenticated (Cookie/JWT) | `editor, manager, admin` | Enforced (company_id via current_user) | Branch CRUD / Warehouse assignment scoped to company | General / Operational |
