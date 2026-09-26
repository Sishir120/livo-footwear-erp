import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User
from app.core.security import get_password_hash

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    comp = db.query(Company).filter(Company.code == "LIVO").first()
    if not comp:
        comp = Company(name="LIVO GROUP OF INDUSTRIES", code="LIVO")
        db.add(comp)
        db.commit()

    ed = db.query(User).filter(User.username == "tally_tester").first()
    if not ed:
        ed = User(
            company_id=comp.id,
            name="Tally Tester",
            username="tally_tester",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(ed)
        db.commit()

    db.close()
    
    with TestClient(app) as test_client:
        test_client.post("/api/v1/auth/login", json={"username": "tally_tester", "password": "Pass123!"})
        yield test_client

def test_tally_daybook_endpoint(client):
    res = client.get("/api/v1/tally/daybook?date_ad=2026-10-01")
    assert res.status_code == 200
    data = res.json()
    assert "vouchers" in data
    assert "total_debit" in data
    assert "total_credit" in data

def test_tally_trial_balance_endpoint(client):
    res = client.get("/api/v1/tally/trial-balance")
    assert res.status_code == 200
    data = res.json()
    assert "groups" in data
    assert "total_debit" in data
    assert "total_credit" in data

def test_tally_profit_loss_endpoint(client):
    res = client.get("/api/v1/tally/profit-loss")
    assert res.status_code == 200
    data = res.json()
    assert "trading_account" in data
    assert "net_profit" in data

def test_tally_outstanding_endpoint(client):
    res = client.get("/api/v1/tally/outstanding")
    assert res.status_code == 200
    data = res.json()
    assert "total_outstanding_receivables" in data
    assert "clients" in data
