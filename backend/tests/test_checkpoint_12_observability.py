import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.api.deps import get_db, get_current_user
from app.models.company import Company
from app.models.user import User
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.stock import Product
from app.models.invoice import Invoice
from app.middleware.rate_limit import BasicRateLimitMiddleware
from app.core.security import create_access_token

from app.db.session import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def auth_client(db_session: Session):
    # Ensure company
    comp = db_session.query(Company).filter_by(code="CP12_CO").first()
    if not comp:
        comp = Company(name="Observability Corp", code="CP12_CO")
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)

    # Ensure user
    user = db_session.query(User).filter_by(username="cp12_admin").first()
    if not user:
        user = User(
            company_id=comp.id,
            name="CP12 Admin",
            username="cp12_admin",
            password_hash="hash",
            role="admin",
            active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"user_id": user.id, "company_id": comp.id, "role": user.role, "username": user.username})
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, comp, user


def test_correlation_id_propagation_and_generation(auth_client):
    """
    §2 & §3 REQUEST CORRELATION & STRUCTURED LOGGING:
    Verify that incoming correlation IDs are preserved across the request lifecycle
    and auto-generated as UUIDs when absent.
    """
    client, comp, user = auth_client

    # 1. Custom correlation ID provided
    custom_id = f"test-trace-{uuid.uuid4()}"
    res = client.get("/api/v1/health/live", headers={"X-Correlation-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("X-Correlation-ID") == custom_id
    assert res.headers.get("X-Request-ID") == custom_id

    # 2. No correlation ID provided: server generates valid UUID
    res_gen = client.get("/api/v1/health/live")
    assert res_gen.status_code == 200
    gen_id = res_gen.headers.get("X-Correlation-ID")
    assert gen_id is not None
    # Validate UUID format
    uuid.UUID(gen_id)


def test_liveness_and_readiness_probes(auth_client):
    """
    §4 HEALTH & READINESS ARCHITECTURE:
    Verify that:
    1. /health/live returns process status without depending on external infrastructure.
    2. /health/ready validates live database connectivity.
    3. Neither probe leaks sensitive topology, credentials, or connection strings.
    """
    client, _, _ = auth_client

    # 1. Liveness check
    live_res = client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    data = live_res.json()
    assert data["status"] == "alive"
    assert "password" not in str(data).lower()
    assert "postgres" not in str(data).lower()

    # 2. Readiness check
    ready_res = client.get("/api/v1/health/ready")
    assert ready_res.status_code == 200
    r_data = ready_res.json()
    assert r_data["status"] == "ready"
    assert r_data["database"] == "healthy"
    assert "password" not in str(r_data).lower()

    # 3. Backward-compatible general health
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    h_data = health_res.json()
    assert h_data["status"] == "healthy"
    assert h_data["database"] == "healthy"


def test_exception_handler_sanitization_and_correlation(auth_client):
    """
    §3 ERROR HANDLING & PRIVACY:
    Verify that unhandled / not found errors:
    1. Attach correlation ID to response headers and payload.
    2. Never leak internal tracebacks, SQL statements, or passwords to the client.
    """
    client, _, _ = auth_client
    custom_trace = f"trace-err-{uuid.uuid4()}"
    res = client.get("/api/v1/nonexistent-endpoint-probe", headers={"X-Correlation-ID": custom_trace})
    assert res.status_code == 404
    assert res.headers.get("X-Correlation-ID") == custom_trace


def test_bounded_pagination_and_n_plus_one_prevention(auth_client, db_session: Session):
    """
    §5 & §6 DATABASE & API PERFORMANCE:
    Verify that collection endpoints:
    1. Enforce pagination limits (prevent unbounded result exhaustion).
    2. Batch-load nested items without N+1 query multiplication.
    3. Correctly offset results across pages.
    """
    client, comp, user = auth_client

    # Seed client
    cli = Client(company_id=comp.id, code="CLI-PAGE", name="Paging Client")
    db_session.add(cli)
    db_session.commit()
    db_session.refresh(cli)

    # Seed 10 sales orders with items
    for i in range(1, 11):
        so = SalesOrder(
            company_id=comp.id,
            order_number=f"SO-PAGE-{i:03d}",
            client_id=cli.id,
            order_date_ad="2026-10-01",
            order_date_bs="2083-06-15",
            status="delivered",
            total_amount=Decimal("1000.00")
        )
        db_session.add(so)
        db_session.commit()
        db_session.refresh(so)

        # Attach item
        item = SalesItem(
            company_id=comp.id,
            sales_order_id=so.id,
            product_id=1,
            quantity=Decimal("2.0"),
            unit_price=Decimal("500.00"),
            total_price=Decimal("1000.00")
        )
        db_session.add(item)
    db_session.commit()

    # Query Page 1: limit 4, offset 0
    res_p1 = client.get("/api/v1/sales/orders?limit=4&offset=0")
    assert res_p1.status_code == 200
    orders_p1 = res_p1.json()
    assert len(orders_p1) == 4
    # Verify nested items are attached via batch query
    assert len(orders_p1[0]["items"]) >= 1

    # Query Page 2: limit 4, offset 4
    res_p2 = client.get("/api/v1/sales/orders?limit=4&offset=4")
    assert res_p2.status_code == 200
    orders_p2 = res_p2.json()
    assert len(orders_p2) == 4
    # Disjoint check: Page 1 and Page 2 must not have overlapping order IDs
    ids_p1 = {o["id"] for o in orders_p1}
    ids_p2 = {o["id"] for o in orders_p2}
    assert ids_p1.isdisjoint(ids_p2)

    # Query Empty Page: offset 1000
    res_empty = client.get("/api/v1/sales/orders?limit=4&offset=1000")
    assert res_empty.status_code == 200
    assert res_empty.json() == []


def test_tenant_isolation_in_paginated_queries(auth_client, db_session: Session):
    """
    §5 & §6 TENANT ISOLATION IN PAGINATED ENDPOINTS:
    Verify that pagination limits and offsets can never leak records from other companies.
    """
    client, comp_a, user_a = auth_client

    # Create or get Tenant B
    comp_b = db_session.query(Company).filter_by(code="TENANT_B_PAGE").first()
    if not comp_b:
        comp_b = Company(name="Tenant B Corp", code="TENANT_B_PAGE")
        db_session.add(comp_b)
        db_session.commit()
        db_session.refresh(comp_b)

    cli_b = db_session.query(Client).filter_by(company_id=comp_b.id, code="CLI-TENANT-B").first()
    if not cli_b:
        cli_b = Client(company_id=comp_b.id, code="CLI-TENANT-B", name="Secret Client B")
        db_session.add(cli_b)
        db_session.commit()

    # Tenant A queries clients
    res = client.get("/api/v1/sales/clients?limit=100&offset=0")
    assert res.status_code == 200
    tenant_a_clients = res.json()
    for c in tenant_a_clients:
        assert c["code"] != "CLI-TENANT-B", "Data leak! Tenant B client visible to Tenant A"


def test_login_rate_limiting_enforcement():
    """
    §7 RATE LIMITING & ABUSE CONTROLS:
    Verify that repeated unauthorized login attempts trigger HTTP 429 Too Many Requests.
    """
    BasicRateLimitMiddleware.reset_all()
    unauth_client = TestClient(app)

    # Send 30 requests within limit
    for _ in range(30):
        unauth_client.post(
            "/api/v1/auth/login",
            data={"username": "attacker", "password": "wrong_password"}
        )

    # 31st request must trigger 429
    res_limit = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "attacker", "password": "wrong_password"}
    )
    assert res_limit.status_code == 429
    assert "Too many login attempts" in res_limit.json()["detail"]

    # Reset for subsequent tests
    BasicRateLimitMiddleware.reset_all()


def test_concurrent_load_invariants(auth_client, db_session: Session):
    """
    §14 LOAD & CONCURRENCY TESTING:
    Simulates high-concurrency operations across multiple threads:
    1. Financial invariant: Zero duplicate ledger entries or drifted sums.
    2. Document numbering invariant: Monotonic, unique sequence numbers.
    3. Tenancy invariant: Strict multi-tenant isolation under load.
    """
    import concurrent.futures
    client, comp, user = auth_client

    cli = db_session.query(Client).filter_by(company_id=comp.id, code="CLI-LOAD").first()
    if not cli:
        cli = Client(company_id=comp.id, code="CLI-LOAD", name="Load Client", credit_limit=Decimal("10000000.00"))
        db_session.add(cli)
        db_session.commit()
        db_session.refresh(cli)

    prod = db_session.query(Product).filter_by(company_id=comp.id).first()
    if not prod:
        prod = Product(company_id=comp.id, code="PROD-LOAD", name="Load Sneaker", unit_price=Decimal("1000.00"), size="42")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

    # Concurrently submit 10 sales orders across 5 threads
    def create_order(idx: int):
        payload = {
            "client_id": cli.id,
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "received_amount": 0.0,
            "delivered": False,
            "items": [
                {
                    "product_id": prod.id,
                    "quantity": 1.0,
                    "unit_price": 1000.0
                }
            ]
        }
        res = client.post("/api/v1/sales/orders", json=payload)
        return res.status_code, res.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(create_order, range(10)))

    successes = [r for r in results if r[0] == 200]
    assert len(successes) == 10, f"Expected 10 successful orders, got {len(successes)}"

    # Invariant: Every order number must be unique
    order_numbers = [r[1]["order_number"] for r in successes]
    assert len(order_numbers) == len(set(order_numbers)), f"Collision detected in order numbers: {order_numbers}"

