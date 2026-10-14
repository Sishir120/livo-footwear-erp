from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "editor_admin"})
    password: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "password123"})

class UserResponse(BaseModel):
    id: int
    company_id: int
    name: str
    username: str
    email: Optional[str] = None
    role: str
    active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    user: UserResponse
    message: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    email: Optional[str] = Field(None, max_length=150)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field("editor", pattern="^(admin|editor|viewer)$")

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[str] = Field(None, max_length=150)
    role: Optional[str] = Field(None, pattern="^(admin|editor|viewer)$")
    active: Optional[bool] = None
