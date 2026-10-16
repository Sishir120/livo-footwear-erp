from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class BranchType(str, Enum):
    HEAD_OFFICE = "HEAD_OFFICE"
    FACTORY = "FACTORY"
    RETAIL_OUTLET = "RETAIL_OUTLET"
    REGIONAL_HUB = "REGIONAL_HUB"


class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: BranchType = BranchType.RETAIL_OUTLET
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)


class BranchCreate(BranchBase):
    code: str = Field(..., min_length=2, max_length=50, description="Unique branch code within company (e.g. BR-KTM-01)")


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    type: Optional[BranchType] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class WarehouseDetailResponse(BaseModel):
    id: int
    name: str
    code: str
    location: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class BranchResponse(BaseModel):
    id: int
    company_id: int
    code: str
    name: str
    type: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    warehouses_count: int = 0
    warehouses: List[WarehouseDetailResponse] = []
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class WarehouseAssignRequest(BaseModel):
    warehouse_id: int = Field(..., description="ID of the warehouse to assign to this branch")
