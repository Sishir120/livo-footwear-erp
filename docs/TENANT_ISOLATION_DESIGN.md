# LIVO FOOTWEAR ERP — TENANT ISOLATION DESIGN

**Checkpoint:** Checkpoint 10 — Authentication, Authorization & Multi-Tenant Security  
**Audit Date:** October 2026  
**Status:** Formally Verified  
**Applies To:** Core Data Access Layer, ORM Models, Sequence Allocators, Offline Queue, Media Storage

---

## 1. Architectural Model: Shared Database, Tenant-Partitioned Tables

LIVO Footwear ERP utilizes a **Shared Database, Shared Schema, Tenant-Partitioned** architecture. Every business-table entity contains a mandatory `company_id: int` foreign key pointing to the authoritative `companies` table.

```text
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│                                                             │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │   Company Alpha (1)   │       │    Company Beta (2)   │  │
│  ├───────────────────────┤       ├───────────────────────┤  │
│  │ Products              │       │ Products              │  │
│  │ Stock Movements       │       │ Stock Movements       │  │
│  │ Sales Orders          │       │ Sales Orders          │  │
│  │ Invoices & Sequences  │       │ Invoices & Sequences  │  │
│  │ Workers & Payroll     │       │ Workers & Payroll     │  │
│  │ Offline Sync Queue    │       │ Offline Sync Queue    │  │
│  │ Product Gallery Media │       │ Product Gallery Media │  │
│  └───────────────────────┘       └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Invariant: Never Trust Client-Supplied Tenant Identifiers

A client must **never** be permitted to specify or override its `company_id`. The authoritative tenant context is derived strictly by the backend security layer:

```text
HTTP Request (HttpOnly Cookie)
       ↓
get_current_user (Dependency)
       ↓
Decode JWT claims -> Extract user_id & company_id
       ↓
Query DB: User.id == user_id AND User.company_id == company_id AND User.active == True
       ↓
current_user.company_id (Authoritative Server Context)
```

### 2.1 Mass-Assignment Neutralization
Even if a malicious client injects `"company_id": 2` or `"is_superuser": true` into request JSON payloads:
1. **Pydantic Schemas:** Schemas such as `ProductCreate`, `ClientCreate`, `SupplierCreate`, and `SalesOrderCreate` explicitly omit `company_id`.
2. **Repository Layer Overwrite:** Even if a dictionary containing `company_id` is unpacked, `TenantRepository.create` forcefully overwrites:
   ```python
   kwargs["company_id"] = self.company_id
   ```
3. **Update Protection:** In `TenantRepository.update`, `kwargs.pop("company_id", None)` strips any attempted company re-assignment.

---

## 3. Database Layer Enforcement: `TenantRepository`

All primary entity operations interact through the generic `TenantRepository[T]` (`backend/app/db/repository.py`):

```python
class TenantRepository(Generic[T]):
    def __init__(self, model: Type[T], db: Session, company_id: int):
        self.model = model
        self.db = db
        self.company_id = company_id
        
        # Invariant check: model must have company_id
        if not hasattr(model, "company_id") and model.__tablename__ != "companies":
            raise ValueError(f"Model {model.__name__} lacks mandatory company_id attribute")

    def get_by_id(self, record_id: Any) -> Optional[T]:
        stmt = select(self.model).where(
            self.model.id == record_id,
            self.model.company_id == self.company_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        stmt = select(self.model).where(
            self.model.company_id == self.company_id
        ).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **kwargs) -> T:
        kwargs["company_id"] = self.company_id
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        return instance

    def update(self, record_id: Any, **kwargs) -> Optional[T]:
        kwargs.pop("company_id", None)  # Prevent tenant reassignment
        instance = self.get_by_id(record_id)
        if not instance:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.db.flush()
        return instance

    def delete(self, record_id: Any) -> bool:
        instance = self.get_by_id(record_id)
        if not instance:
            return False
        self.db.delete(instance)
        self.db.flush()
        return True
```

### Defense Against IDOR (Insecure Direct Object Reference)
Because `get_by_id` executes:
```sql
SELECT * FROM table WHERE id = :record_id AND company_id = :auth_company_id
```
If a user from Company A queries `/invoices/42` where invoice 42 belongs to Company B:
- `get_by_id` returns `None`.
- The endpoint raises `HTTPException(404, "Invoice not found")`.
- Company A is never informed whether invoice 42 even exists. Data leakage is zero.

---

## 4. Secondary Queries, Joins & Aggregations

In complex analytical and reporting queries, joins must enforce `company_id` on all participating tables to prevent accidental cross-tenant row exposure.

### 4.1 Stock Ledger Batch Lookups
When generating the tabular stock ledger (`GET /api/v1/stock/ledger`), batch lookups for products, warehouses, and users enforce:
```python
prods = {p.id: p for p in db.query(Product).filter(Product.id.in_(p_ids), Product.company_id == current_user.company_id).all()}
warehouses = {w.id: w for w in db.query(Warehouse).filter(Warehouse.id.in_(w_ids), Warehouse.company_id == current_user.company_id).all()}
users = {u.id: u for u in db.query(User).filter(User.id.in_(u_ids), User.company_id == current_user.company_id).all()}
```

### 4.2 Reports & Analytics Subqueries
In `/analytics/top-products`, joins between `SalesItem` and `SalesOrder` carry company-scoping on both sides:
```python
sales_subquery = db.query(
    SalesItem.product_id,
    func.sum(SalesItem.quantity).label("total_pairs_sold"),
    func.sum(SalesItem.total_price).label("total_revenue")
).join(
    SalesOrder, SalesItem.sales_order_id == SalesOrder.id
).filter(
    SalesItem.company_id == current_user.company_id,
    SalesOrder.company_id == current_user.company_id,
    SalesOrder.status != "cancelled"
).group_by(SalesItem.product_id).subquery()
```

---

## 5. Partitioning of Supporting Subsystems

### 5.1 Document Sequencing
Document sequences (`invoice_sequences` table) are scoped per company:
```sql
SELECT current_sequence FROM invoice_sequences 
WHERE company_id = :company_id FOR UPDATE
```
Company A and Company B each maintain independent monotonic sequences starting from 1. Formatted document numbers include the company identifier (e.g. `INV-01-00001` vs `INV-02-00001`).

### 5.2 Offline Synchronization Queue
As proven in Checkpoint 9, IndexedDB v2 stores every queued mutation with an explicit `companyId` partition key:
```typescript
interface OfflineQueueItem {
  id?: number;
  companyId: number;  // Mandatory tenant boundary
  endpoint: string;
  payload: Record<string, any>;
  status: QueueItemStatus;
}
```
When processing queued offline operations upon reconnect, the queue engine queries exclusively records matching `companyId == currentCompanyId`. When switching companies, other tenants' queued operations remain dormant.

### 5.3 Media & File Storage
In `/api/v1/gallery`:
- Image file uploads are stored on disk with randomized non-guessable UUID filenames (`{uuid}_{sanitized_name}`).
- Database metadata records `company_id`.
- The download endpoint (`GET /api/v1/gallery/images/{image_id}/download`) queries `ProductImage.id == image_id, ProductImage.company_id == current_user.company_id`. Attempting to access an image belonging to another company returns HTTP 404.

---

## 6. Verification & Automated Test Evidence

Automated tests in `backend/tests/test_checkpoint_10_security.py` and `backend/tests/test_security_audit.py` provide evidence of tenant isolation:

1. **`test_cross_tenant_idor_protection_across_all_entities`:**  
   Proves that Company Beta receives HTTP 404 when attempting direct GET access to Alpha's Clients, Suppliers, Raw Materials, Products, Batches, Warehouses, Orders, Invoices, and Printable Views.
2. **`test_client_supplied_tenant_id_mass_assignment_neutralized`:**  
   Proves that injecting arbitrary `company_id` values in creation payloads is completely ignored in favor of the server's security context.
3. **`test_reports_and_analytics_tenant_partitioning`:**  
   Proves that daily reports, stock reports, and analytics metrics for Company Alpha never leak into Company Beta's aggregations.
4. **`test_document_numbering_cross_tenant_independence`:**  
   Proves that invoice sequences for Alpha and Beta increment independently without interference.
5. **`test_user_management_cross_tenant_idor`:**  
   Proves that an administrator of Company Alpha cannot list, view, or modify users belonging to Company Beta.
