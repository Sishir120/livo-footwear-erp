from typing import TypeVar, Generic, Type, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.db.session import Base

T = TypeVar("T", bound=Base)

class TenantRepository(Generic[T]):
    """
    Mandatory tenant-scoped repository helper for business models.
    Enforces company_id scoping on every single query, insert, update, and delete
    as required by RULES.md §0 and §9 to prevent cross-tenant data leaks.
    """
    def __init__(self, model: Type[T], db: Session, company_id: int):
        self.model = model
        self.db = db
        self.company_id = company_id
        
        # Invariant enforcement check: Model MUST have company_id attribute unless it's the root Company model
        is_company_model = getattr(model, "__tablename__", "") == "companies"
        if not hasattr(model, "company_id"):
            if is_company_model:
                raise ValueError(f"Model {model.__name__} is the tenant model itself and cannot be wrapped in TenantRepository")
            raise ValueError(f"Model {model.__name__} does not have mandatory company_id attribute")

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

    def filter(self, *criterion, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        stmt = select(self.model).where(
            self.model.company_id == self.company_id,
            *criterion
        ).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def filter_one(self, *criterion) -> Optional[T]:
        stmt = select(self.model).where(
            self.model.company_id == self.company_id,
            *criterion
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs) -> T:
        # Enforce company_id on created record
        kwargs["company_id"] = self.company_id
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def update(self, record_id: Any, **kwargs) -> Optional[T]:
        # Strip out company_id if present to prevent tenant re-assignment
        kwargs.pop("company_id", None)
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
