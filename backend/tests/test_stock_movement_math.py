import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models import Company, Product, StockMovement
from app.db.repository import TenantRepository

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    comp = Company(id=1, name="LIVO GROUP OF INDUSTRIES", code="LIVO")
    session.add(comp)
    session.commit()
    
    yield session
    session.close()

def get_product_stock_balance(db_session, company_id: int, product_id: int) -> float:
    """Helper function computing stock directly from movement logs per RULES.md §1"""
    result = db_session.query(
        func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
    ).filter(
        StockMovement.company_id == company_id,
        StockMovement.product_id == product_id
    ).scalar()
    return float(result)

def test_stock_movement_ledger_calculation(db):
    product_repo = TenantRepository(Product, db, company_id=1)
    movement_repo = TenantRepository(StockMovement, db, company_id=1)
    
    # 1. Create a product
    shoe = product_repo.create(
        code="SHOE-BLK-42",
        name="Leather Boot Black Size 42",
        category="Boot",
        size="42",
        color="Black",
        unit_price=2500.0
    )
    db.commit()
    
    # Initial balance should be 0
    assert get_product_stock_balance(db, company_id=1, product_id=shoe.id) == 0.0

    # 2. Production batch finished -> 100 pairs produced (+1 IN)
    movement_repo.create(
        product_id=shoe.id,
        quantity=100.0,
        direction=1,
        ref_type="production",
        ref_id=101,
        date_ad="2026-09-25",
        date_bs="2083-06-09",
        notes="Batch 101 production"
    )
    db.commit()
    assert get_product_stock_balance(db, company_id=1, product_id=shoe.id) == 100.0

    # 3. Sale order delivered -> 30 pairs sold (-1 OUT)
    movement_repo.create(
        product_id=shoe.id,
        quantity=30.0,
        direction=-1,
        ref_type="sale",
        ref_id=501,
        date_ad="2026-09-25",
        date_bs="2083-06-09",
        notes="Sale order 501"
    )
    db.commit()
    assert get_product_stock_balance(db, company_id=1, product_id=shoe.id) == 70.0

    # 4. Customer return -> 5 pairs returned (+1 IN)
    movement_repo.create(
        product_id=shoe.id,
        quantity=5.0,
        direction=1,
        ref_type="return",
        ref_id=501,
        date_ad="2026-09-25",
        date_bs="2083-06-09",
        notes="Return from sale 501"
    )
    db.commit()
    assert get_product_stock_balance(db, company_id=1, product_id=shoe.id) == 75.0
