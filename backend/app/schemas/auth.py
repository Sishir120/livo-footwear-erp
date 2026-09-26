from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str = Field(..., json_schema_extra={"example": "editor_admin"})
    password: str = Field(..., json_schema_extra={"example": "password123"})

class UserResponse(BaseModel):
    id: int
    company_id: int
    name: str
    username: str
    email: Optional[str] = None
    role: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    user: UserResponse
    message: str
