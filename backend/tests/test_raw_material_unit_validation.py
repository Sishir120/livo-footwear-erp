import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.core.security import get_password_hash
from app.models.purchase import RawMaterial

@pytest.fixture
def setup_raw_material_env():
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.name == "Raw Material Unit Test Co").first()
        if not company:
            company = Company(name="Raw Material Unit Test Co", code="RM-CO-1", pan_number="308888888")
            db.add(company)
            db.commit()
            db.refresh(company)

        editor = db.query(User).filter(User.username == "rm_editor").first()
        if not editor:
            editor = User(
                company_id=company.id,
                username="rm_editor",
                name="RM Editor",
                password_hash=get_password_hash("RmPass2026!"),
                role="editor",
                active=True
            )
            db.add(editor)
            db.commit()

        yield {"company_id": company.id}
    finally:
        db.close()


def _login(client: TestClient):
    res = client.post("/api/v1/auth/login", json={"username": "rm_editor", "password": "RmPass2026!"})
    assert res.status_code == 200


def test_valid_units_accepted(setup_raw_material_env):
    """Verifies that all three supported units ('kg', 'pcs', 'litre') are accepted."""
    with TestClient(app) as client:
        _login(client)

        for unit in ["kg", "pcs", "litre"]:
            res = client.post("/api/v1/purchase/raw-materials", json={
                "code": f"RM-VALID-{unit.upper()}",
                "name": f"Raw Material in {unit}",
                "unit": unit,
                "reorder_level": 50.0,
                "min_stock_alert": 20.0
            })
            assert res.status_code == 200, f"Expected 200 for unit '{unit}', got {res.status_code}: {res.text}"
            data = res.json()
            assert data["unit"] == unit
            assert data["code"] == f"RM-VALID-{unit.upper()}"


def test_invalid_units_return_422_not_500(setup_raw_material_env):
    """
    Verifies that unsupported, uppercase, or malformed units are rejected with HTTP 422
    at the schema validation boundary without triggering a database check-constraint 500 error.
    """
    with TestClient(app) as client:
        _login(client)

        invalid_units = [
            "ton",
            "meter",
            "yard",
            "KG",       # Case-sensitive check
            "PCS",
            "LITRE",
            "gram",
            "box",
            "",
            "123"
        ]

        db = SessionLocal()
        initial_count = db.query(RawMaterial).count()
        db.close()

        for bad_unit in invalid_units:
            res = client.post("/api/v1/purchase/raw-materials", json={
                "code": f"RM-BAD-{bad_unit}",
                "name": f"Invalid unit test {bad_unit}",
                "unit": bad_unit
            })
            assert res.status_code == 422, f"Expected 422 for unit '{bad_unit}', got {res.status_code}: {res.text}"

        # Confirm zero dirty records persisted
        db = SessionLocal()
        final_count = db.query(RawMaterial).count()
        db.close()
        assert final_count == initial_count, "Invalid unit attempts must not insert database records"


def test_raw_material_update_unit_validation(setup_raw_material_env):
    """Verifies that PATCH /raw-materials/{id} enforces the same unit validation."""
    with TestClient(app) as client:
        _login(client)

        # 1. Create a valid raw material in 'kg'
        create_res = client.post("/api/v1/purchase/raw-materials", json={
            "code": "RM-UPD-01",
            "name": "Leather Sheet Grade A",
            "unit": "kg"
        })
        assert create_res.status_code == 200
        mat_id = create_res.json()["id"]

        # 2. Update to valid unit 'pcs'
        upd_valid = client.patch(f"/api/v1/purchase/raw-materials/{mat_id}", json={
            "unit": "pcs"
        })
        assert upd_valid.status_code == 200
        assert upd_valid.json()["unit"] == "pcs"

        # 3. Attempt update to invalid unit 'ton' -> must be 422
        upd_invalid = client.patch(f"/api/v1/purchase/raw-materials/{mat_id}", json={
            "unit": "ton"
        })
        assert upd_invalid.status_code == 422

        # 4. Verify unit remains 'pcs'
        get_res = client.get(f"/api/v1/purchase/raw-materials/{mat_id}")
        assert get_res.status_code == 200
        assert get_res.json()["unit"] == "pcs"
