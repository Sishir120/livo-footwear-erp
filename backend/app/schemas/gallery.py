from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_id: int
    product_code: str
    product_name: str
    category: Optional[str] = None
    image_url: str
    file_name: str
    mime_type: str
    file_size_bytes: Optional[int] = None
    is_primary: bool
    created_at: datetime
