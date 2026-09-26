import pytest
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from app.db.repository import TenantRepository

TestBase = declarative_base()

class MockCompany(TestBase):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

class MockProduct(TestBase):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100))

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create 2 companies for tenant isolation test
    c1 = MockCompany(id=1, name="LIVO Group")
    c2 = MockCompany(id=2, name="Competitor Footwear")
    session.add_all([c1, c2])
    session.commit()
    
    yield session
    session.close()

def test_tenant_repository_isolation(db_session):
    repo1 = TenantRepository(MockProduct, db_session, company_id=1)
    repo2 = TenantRepository(MockProduct, db_session, company_id=2)
    
    # Create products for Company 1
    p1 = repo1.create(name="LIVO Boot Red Size 42")
    p2 = repo1.create(name="LIVO Slipper Black Size 39")
    
    # Create product for Company 2
    p3 = repo2.create(name="Competitor Boot")
    
    db_session.commit()
    
    # Verify Tenant 1 only sees Company 1 products
    t1_products = repo1.get_all()
    assert len(t1_products) == 2
    assert all(p.company_id == 1 for p in t1_products)
    
    # Verify Tenant 2 only sees Company 2 products
    t2_products = repo2.get_all()
    assert len(t2_products) == 1
    assert t2_products[0].company_id == 2
    assert t2_products[0].name == "Competitor Boot"
    
    # Verify Tenant 1 cannot access Tenant 2 product by ID
    assert repo1.get_by_id(p3.id) is None

class MockInvalidModel(TestBase):
    __tablename__ = "invalid_models"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

def test_tenant_repository_rejects_model_without_company_id(db_session):
    with pytest.raises(ValueError, match="is the tenant model itself"):
        TenantRepository(MockCompany, db_session, company_id=1)
        
    with pytest.raises(ValueError, match="does not have mandatory company_id attribute"):
        TenantRepository(MockInvalidModel, db_session, company_id=1)
