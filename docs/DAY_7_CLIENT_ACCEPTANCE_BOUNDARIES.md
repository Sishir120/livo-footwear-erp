# LIVO Footwear ERP — Day 7 Client Acceptance Boundaries & Capability Matrix

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Client Demonstration Boundary & Operational Transparency  
**Demonstration Scope:** Controlled 1-Week Synthetic Evaluation

---

## 1. Executive Summary

To ensure clear communication and prevent client expectation mismatches during the demonstration, every ERP business capability was audited across source code, backend routes, React components, and automated test suites. 

Capabilities are classified into five concrete readiness states:
1. **Verified in UI and Backend:** Fully implemented, navigable in browser, and backed by passing database integration tests.
2. **Backend Only:** Fully functional via API endpoints, but lacks dedicated frontend UI workflow.
3. **UI Only or Incomplete:** Partially implemented in frontend with rough edges or incomplete integrations.
4. **Not Implemented:** Not present in the active codebase.
5. **Not Verified:** Exists in codebase but unverified by tests during this release gate.

---

## 2. Business Capability Audit Matrix

| ERP Capability | Implementation Details | Evidence (Routes & Components) | Classification |
| :--- | :--- | :--- | :---: |
| **Procurement, Goods Receipt & Landed Costs** | Multi-item purchase orders, customs/freight landed cost capitalization, and automatic raw material stock updates on GRN. | `api/v1/purchase.py`, `PurchaseView.tsx`, `test_raw_material_ledger.py` | **Verified in UI and Backend** |
| **Raw Material Inventory & Units** | Stock tracking by unit (meters, kg, rolls, pairs), minimum threshold alerts, and inventory ledger movements. | `api/v1/purchase.py`, `PurchaseView.tsx`, `test_raw_material_unit_validation.py` | **Verified in UI and Backend** |
| **Production Batches & Multi-Size Inventory** | Production run batch tracking, automated BOM raw material deductions, and variant inventory replenishment (size/color). | `api/v1/production.py`, `ProductionView.tsx`, `test_bom_deduction.py` | **Verified in UI and Backend** |
| **Branch Transfers & Destination Receipts** | Inter-warehouse transfers, in-transit status tracking, and destination receipt confirmation. | `api/v1/transfers.py`, `StockTransferModal.tsx`, `test_stock_transfers.py` | **Verified in UI and Backend** |
| **Sales, Dispatch, Invoices, Payments & VAT** | Order entry, dispatch validation, statutory Nepal 13% VAT invoicing, credit notes, and AR payment tracking. | `api/v1/invoices.py`, `api/v1/sales.py`, `SalesInvoiceView.tsx`, `test_vat_compliance_and_calculation.py` | **Verified in UI and Backend** |
| **HR Profiles, Salary Privacy & Document RBAC** | Worker registry, advance disbursements, payroll calculation, viewer compensation masking, and confidential citizenship uploads. | `api/v1/hr.py`, `HRManagementView.tsx`, `test_hr_management.py` | **Verified in UI and Backend** |
| **Expenses, Fixed Assets & Scrap / Waste** | Factory operational expenses, fixed asset registry with straight-line depreciation, and scrap/reject tracking. | `api/v1/assets.py`, `ExpensesAssetsView.tsx`, `test_fixed_assets_waste_and_expenses.py` | **Verified in UI and Backend** |
| **Mandatory Batch Assignment at Dispatch** | Dispatch allocates inventory strictly by Product Variant (SKU) and size. The schema does not enforce physical batch serial linking. | `backend/app/models/sales.py`, `backend/app/models/stock.py` | **Not Implemented** |
| **Bikram Sambat (BS) / AD Date Workflows** | Backend bidirectional date converter is fully tested. However, frontend form inputs default to Gregorian HTML5 date pickers. | `backend/app/core/nepali_date.py`, `frontend/src/components/*` | **UI Only or Incomplete** |
| **Contextual Help & Searchable Documentation** | Markdown documentation exists in repo (`docs/`). No searchable in-app documentation modal or bilingual help center exists in the UI. | `docs/*.md` | **Not Implemented** |
| **Formal Double-Entry General Ledger & Trial Balance** | ERP contains AR sub-ledgers and sales/purchase records. It does NOT contain a formal Chart of Accounts or debit/credit journal ledger. | Planned for future roadmap | **Not Implemented** |
| **Multi-Device Offline Synchronization** | Backend accepts `X-Idempotency-Key` headers for network retry safety. Multi-device background sync across intermittent links is unproven. | `backend/app/api/deps.py`, `test_idempotency.py` | **Backend Only** |

---

## 3. Evaluator Disclosure Guidelines

Demonstrators must explicitly disclose to client evaluators:
1. **Focus on Manufacturing & Inventory Operations:** Highlight the strong footwear production flows: BOM consumption, landed costs, inter-warehouse transfers, and VAT invoicing.
2. **Accounting Scope:** Clarify that LIVO ERP handles operational invoicing, tax calculations, and accounts receivable, but delegates full trial-balance statutory accounting to specialized packages or future accounting modules.
3. **Traceability:** Dispatches verify variant availability in stock, but do not constrain dispatches to specific production batch IDs.
