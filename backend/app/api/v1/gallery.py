import os
import uuid
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product
from app.models.gallery import ProductImage
from app.schemas.gallery import ProductImageResponse

router = APIRouter(prefix="/gallery", tags=["Product Gallery"])

# Upload directory: backend/static/uploads/products
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "static",
    "uploads",
    "products"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    return clean[:100] if len(clean) > 100 else clean


@router.post("/upload/{product_id}", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Upload a product image (JPEG, PNG, WEBP <= 5MB) and attach it to a product.
    Enforces multi-tenant scoping and editor permissions.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == current_user.company_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product #{product_id} not found in your company catalog"
        )

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Allowed formats: JPEG, PNG, WEBP."
        )

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 5 MB (size: {len(content) / (1024 * 1024):.2f} MB)."
        )

    safe_original_name = _sanitize_filename(file.filename or "product_image.jpg")
    unique_file_name = f"{uuid.uuid4().hex[:12]}_{safe_original_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_file_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Set previous images of this product to not primary if this is primary
    db.query(ProductImage).filter(
        ProductImage.company_id == current_user.company_id,
        ProductImage.product_id == product.id
    ).update({"is_primary": False})

    new_image = ProductImage(
        company_id=current_user.company_id,
        product_id=product.id,
        image_url=f"/api/v1/gallery/images/temp/download",  # placeholder updated below with ID
        file_name=file.filename or safe_original_name,
        mime_type=file.content_type or "image/jpeg",
        file_size_bytes=len(content),
        is_primary=True
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    # Update real download URL
    new_image.image_url = f"/api/v1/gallery/images/{new_image.id}/download"
    # Store internal disk filename in image_url or we can look it up; let's store it safely
    # We can use the file_path basename
    new_image.file_name = unique_file_name
    db.commit()
    db.refresh(new_image)

    return ProductImageResponse(
        id=new_image.id,
        company_id=new_image.company_id,
        product_id=product.id,
        product_code=product.code,
        product_name=product.name,
        category=product.category,
        image_url=new_image.image_url,
        file_name=file.filename or safe_original_name,
        mime_type=new_image.mime_type,
        file_size_bytes=new_image.file_size_bytes,
        is_primary=new_image.is_primary,
        created_at=new_image.created_at
    )


@router.get("", response_model=List[ProductImageResponse])
def get_gallery_items(
    search: Optional[str] = Query(None, description="Search by product code or name"),
    category: Optional[str] = Query(None, description="Filter by footwear category"),
    product_id: Optional[int] = Query(None, description="Filter by specific product ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List product gallery items with product metadata for the active company.
    """
    query = db.query(ProductImage, Product).join(
        Product, ProductImage.product_id == Product.id
    ).filter(
        ProductImage.company_id == current_user.company_id,
        Product.company_id == current_user.company_id
    )

    if product_id:
        query = query.filter(ProductImage.product_id == product_id)

    if category:
        query = query.filter(Product.category == category)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.code.ilike(term),
                Product.name.ilike(term)
            )
        )

    results = query.order_by(ProductImage.created_at.desc()).all()

    items = []
    for img, prod in results:
        items.append(
            ProductImageResponse(
                id=img.id,
                company_id=img.company_id,
                product_id=prod.id,
                product_code=prod.code,
                product_name=prod.name,
                category=prod.category,
                image_url=f"/api/v1/gallery/images/{img.id}/download",
                file_name=img.file_name,
                mime_type=img.mime_type,
                file_size_bytes=img.file_size_bytes,
                is_primary=img.is_primary,
                created_at=img.created_at
            )
        )
    return items


@router.get("/images/{image_id}/download")
def download_product_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stream or download product image file with multi-tenant scoping.
    """
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.company_id == current_user.company_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image #{image_id} not found"
        )

    file_path = os.path.join(UPLOAD_DIR, image.file_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on server disk"
        )

    return FileResponse(
        path=file_path,
        media_type=image.mime_type,
        filename=image.file_name
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Delete a product image reference and its file from disk. Enforces editor role.
    """
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.company_id == current_user.company_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image #{image_id} not found"
        )

    file_path = os.path.join(UPLOAD_DIR, image.file_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.delete(image)
    db.commit()
    return None
