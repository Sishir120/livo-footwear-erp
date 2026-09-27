import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User
from app.core.security import get_password_hash

@pytest.fixture(scope="module")
def client():
    # Setup test database tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Ensure test company exists
    comp = db.query(Company).filter(Company.code == "LIVO").first()
    if not comp:
        comp = Company(name="LIVO GROUP OF INDUSTRIES", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)
        
    # Ensure test editor exists
    ed = db.query(User).filter(User.username == "test_editor").first()
    if not ed:
        ed = User(
            company_id=comp.id,
            name="Test Editor",
            username="test_editor",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(ed)

    # Ensure test viewer exists
    vw = db.query(User).filter(User.username == "test_viewer").first()
    if not vw:
        vw = User(
            company_id=comp.id,
            name="Test Viewer",
            username="test_viewer",
            password_hash=get_password_hash("Pass123!"),
            role="viewer",
            active=True
        )
        db.add(vw)

    db.commit()
    db.close()
    
    with TestClient(app) as test_client:
        yield test_client

def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "healthy")
    assert data["version"] == "1.0.0"

def test_login_and_me_flow(client):
    # Test login
    login_res = client.post("/api/v1/auth/login", json={"username": "test_editor", "password": "Pass123!"})
    assert login_res.status_code == 200
    assert "livo_access_token" in login_res.cookies
    
    # Test /me with cookie
    me_res = client.get("/api/v1/auth/me", cookies=login_res.cookies)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["username"] == "test_editor"
    assert user_data["role"] == "editor"

def test_login_invalid_credentials(client):
    res = client.post("/api/v1/auth/login", json={"username": "test_editor", "password": "WrongPassword"})
    assert res.status_code == 401
