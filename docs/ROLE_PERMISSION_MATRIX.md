# LIVO FOOTWEAR ERP — ROLE & PERMISSION MATRIX

**Checkpoint:** Checkpoint 10 — Authentication, Authorization & Multi-Tenant Security  
**Audit Date:** October 2026  
**Status:** Formally Verified  

---

## 1. Overview of Implemented Roles

LIVO Footwear ERP defines three distinct roles derived directly from business operations and statutory audit requirements:

1. **`admin` (System Administrator / Executive Operator):**  
   Responsible for system integrity, database backup executions, administrative cockpit telemetry, and user access provisioning.
2. **`editor` (Factory Operations Manager / Sales & Production Operator):**  
   Responsible for day-to-day manufacturing, inventory management, order execution, accounts receivable, and workforce tracking.
3. **`viewer` (Compliance Auditor / Management Viewer / External Accountant):**  
   Permitted read-only visibility into financial ledgers, inventory balances, production runs, and audit logs. Strictly blocked from mutating data.

---

## 2. High-Level Capability Matrix

| Capability | `admin` | `editor` | `viewer` | Enforcement Boundary |
|---|:---:|:---:|:---:|---|
| **Can View Business Data** | ✅ Yes | ✅ Yes | ✅ Yes | `get_current_user` + `TenantRepository` |
| **Can View Reports & Analytics** | ✅ Yes | ✅ Yes | ✅ Yes | `get_current_user` + `company_id` filter |
| **Can View Operations Cockpit** | ✅ Yes | ❌ No (403) | ❌ No (403) | `require_admin` |
| **Can Create Orders & Clients** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Create Production Batches** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Generate Tax Invoices** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Cancel/Void Invoices** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Post AR Adjustments** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Post Stock Adjustments** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` + Supervisor Token |
| **Can Reverse Stock Movements** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` + Supervisor Token |
| **Can Manage HR & Workers** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Upload/Delete Images** | ✅ Yes | ✅ Yes | ❌ No (403) | `require_editor` |
| **Can Trigger Database Backups** | ✅ Yes | ❌ No (403) | ❌ No (403) | `require_admin` |
| **Can View & Manage Users** | ✅ Yes | ❌ No (403) | ❌ No (403) | `require_admin` |
| **Can Modify Audit Records** | ❌ No (405) | ❌ No (405) | ❌ No (405) | Database append-only; no API |

---

## 3. Detailed Endpoint Permission Mapping

### 3.1 Authentication & User Management (`/api/v1/auth`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Authenticates credentials and sets session cookie |
| `POST` | `/auth/logout` | Public | Clears authentication session cookie |
| `GET` | `/auth/me` | Authenticated | Retrieves current user context |
| `GET` | `/auth/users` | `admin` | Lists tenant users |
| `POST` | `/auth/users` | `admin` | Provisions new user in tenant |
| `PATCH` | `/auth/users/{user_id}` | `admin` | Updates tenant user active/role status |

### 3.2 Sales & Receivables (`/api/v1/sales` & `/api/v1/receivables`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/sales/clients` | Authenticated | Lists company clients |
| `GET` | `/sales/clients/{id}` | Authenticated | Fetches single client record |
| `POST` | `/sales/clients` | `editor`, `admin` | Creates new client record |
| `GET` | `/sales/orders` | Authenticated | Lists company sales orders |
| `GET` | `/sales/orders/{id}` | Authenticated | Fetches single sales order |
| `POST` | `/sales/orders` | `editor`, `admin` | Creates sales order (locks stock & credit) |
| `POST` | `/sales/payments` | `editor`, `admin` | Records client payment on sales order |
| `GET` | `/receivables/statement/{client_id}` | Authenticated | Generates client AR ledger statement |
| `POST` | `/receivables/entries` | `editor`, `admin` | Posts manual AR debit/credit adjustment |
| `POST` | `/receivables/settle` | `editor`, `admin` | Executes FIFO payment settlement |

### 3.3 Invoicing & Statutory VAT (`/api/v1/invoices`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/invoices` | Authenticated | Lists company invoices |
| `GET` | `/invoices/{id}` | Authenticated | Fetches single invoice |
| `GET` | `/invoices/{id}/printable` | Authenticated | Renders XSS-sanitized printable invoice HTML |
| `POST` | `/invoices` | `editor`, `admin` | Issues statutory invoice with atomic sequence |
| `POST` | `/invoices/{id}/cancel` | `editor`, `admin` | Voids invoice and posts AR VOID_REVERSAL |

### 3.4 Production & Materials (`/api/v1/production` & `/api/v1/purchase`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/production/products` | Authenticated | Lists company products |
| `GET` | `/production/products/{id}` | Authenticated | Fetches single product |
| `POST` | `/production/products` | `editor`, `admin` | Creates new product definition |
| `GET` | `/production/bom` | Authenticated | Lists bill of materials |
| `POST` | `/production/bom` | `editor`, `admin` | Configures BOM recipe for product |
| `GET` | `/production/batches` | Authenticated | Lists production batch history |
| `GET` | `/production/batches/{id}` | Authenticated | Fetches single batch |
| `POST` | `/production/batches` | `editor`, `admin` | Executes production run and stock deduction |
| `GET` | `/purchase/suppliers` | Authenticated | Lists suppliers |
| `GET` | `/purchase/suppliers/{id}` | Authenticated | Fetches single supplier |
| `POST` | `/purchase/suppliers` | `editor`, `admin` | Creates new supplier profile |
| `GET` | `/purchase/raw-materials` | Authenticated | Lists raw materials inventory |
| `GET` | `/purchase/raw-materials/{id}` | Authenticated | Fetches single raw material |
| `POST` | `/purchase/raw-materials` | `editor`, `admin` | Creates raw material definition |
| `GET` | `/purchase/purchases` | Authenticated | Lists material purchases |
| `GET` | `/purchase/purchases/{id}` | Authenticated | Fetches single purchase |
| `POST` | `/purchase/purchases` | `editor`, `admin` | Records raw material receipt |

### 3.5 Stock Ledger & Warehouses (`/api/v1/stock`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/stock/movements` | Authenticated | Lists append-only stock ledger movements |
| `POST` | `/stock/movements` | `editor`, `admin` | Appends stock movement (+1 IN or -1 OUT) |
| `GET` | `/stock/balance` | Authenticated | Queries O(1) snapshot-accelerated stock |
| `GET` | `/stock/snapshots` | Authenticated | Lists historical daily snapshots |
| `POST` | `/stock/snapshots` | `editor`, `admin` | Generates stock balance snapshot |
| `GET` | `/stock/warehouses` | Authenticated | Lists active warehouses |
| `GET` | `/stock/warehouses/{id}` | Authenticated | Fetches single warehouse |
| `GET` | `/stock/ledger` | Authenticated | Tabular stock ledger with preloaded metadata |
| `POST` | `/stock/adjustments` | `editor`, `admin` | Posts physical inventory adjustment |
| `POST` | `/stock/reversals/{id}` | `editor`, `admin` | Posts compensatory reversal movement |

### 3.6 Human Resources & Payroll (`/api/v1/hr`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/hr/workers` | Authenticated | Lists workers with real-time advances and hours |
| `POST` | `/hr/workers` | `editor`, `admin` | Creates new worker profile |
| `PATCH` | `/hr/workers/{id}` | `editor`, `admin` | Updates worker profile or toggles active status |
| `GET` | `/hr/advances` | Authenticated | Lists worker cash advances |
| `POST` | `/hr/advances` | `editor`, `admin` | Issues or recovers advance |
| `POST` | `/hr/payroll` | `editor`, `admin` | Finalizes monthly payroll ledger record |

### 3.7 Product Gallery & Media (`/api/v1/gallery`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/gallery` | Authenticated | Lists company gallery items |
| `GET` | `/gallery/images/{id}/download` | Authenticated | Streams image file scoped to company |
| `POST` | `/gallery/upload/{product_id}` | `editor`, `admin` | Uploads JPEG/PNG/WEBP product photo |
| `DELETE` | `/gallery/{id}` | `editor`, `admin` | Deletes product photo reference and file |

### 3.8 Operations, Telemetry & Backups (`/api/v1/ops` & `/api/v1/backup`)
| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/ops/telemetry` | `admin` | Supervisor telemetry & health cockpit |
| `GET` | `/backup/status` | Authenticated | Queries database backup status |
| `POST` | `/backup/run` | `admin` | Triggers immediate database backup |
| `GET` | `/diagnostics/download` | `admin` | Downloads system diagnostics archive |
