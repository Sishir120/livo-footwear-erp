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
from app.models.production import ProductionBatch
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
    production_batch_id: Optional[int] = Query(None, description="Optional associated production batch ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Upload a product image (JPEG, PNG, WEBP <= 5MB) and attach it to a product (and optionally a production batch).
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

    batch = None
    if production_batch_id is not None:
        batch = db.query(ProductionBatch).filter(
            ProductionBatch.id == production_batch_id,
            ProductionBatch.company_id == current_user.company_id
        ).first()

        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Production batch #{production_batch_id} not found in your company"
            )

        if batch.product_id != product.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Production batch #{production_batch_id} belongs to product #{batch.product_id}, not product #{product.id}"
            )

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Allowed formats: JPEG, PNG, WEBP."
        )

    # Validate file extension
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    raw_filename = file.filename or ""
    ext = os.path.splitext(raw_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed extensions: .jpg, .jpeg, .png, .webp"
        )

    # Prevent double extension execution tricks (e.g., payload.php.jpg)
    stem = os.path.splitext(raw_filename)[0]
    if any(stem.lower().endswith(bad) for bad in [".exe", ".php", ".sh", ".bat", ".cmd", ".py", ".pl", ".dll"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dangerous multi-extension filename detected."
        )

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 5 MB (size: {len(content) / (1024 * 1024):.2f} MB)."
        )

    # Validate header magic bytes
    is_valid_magic = (
        content.startswith(b"\xff\xd8\xff") or  # JPEG
        content.startswith(b"\x89PNG\r\n\x1a\n") or  # PNG
        (len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")  # WEBP
    )
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image payload: file content does not match image header signatures."
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
        production_batch_id=batch.id if batch else None,
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
        created_at=new_image.created_at,
        production_batch_id=batch.id if batch else None,
        batch_number=batch.batch_number if batch else None,
        batch_color=(batch.color or product.color) if batch else product.color,
        batch_date_bs=batch.date_bs if batch else None,
    )


@router.get("", response_model=List[ProductImageResponse])
def get_gallery_items(
    search: Optional[str] = Query(None, description="Search by product code or name"),
    category: Optional[str] = Query(None, description="Filter by footwear category"),
    product_id: Optional[int] = Query(None, description="Filter by specific product ID"),
    production_batch_id: Optional[int] = Query(None, description="Filter by specific production batch ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List product gallery items with product and production batch metadata for the active company.
    """
    query = db.query(ProductImage, Product, ProductionBatch).join(
        Product, ProductImage.product_id == Product.id
    ).outerjoin(
        ProductionBatch, ProductImage.production_batch_id == ProductionBatch.id
    ).filter(
        ProductImage.company_id == current_user.company_id,
        Product.company_id == current_user.company_id
    )

    if product_id:
        query = query.filter(ProductImage.product_id == product_id)

    if production_batch_id:
        query = query.filter(ProductImage.production_batch_id == production_batch_id)

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
    for img, prod, batch in results:
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
                created_at=img.created_at,
                production_batch_id=batch.id if batch else None,
                batch_number=batch.batch_number if batch else None,
                batch_color=(batch.color or prod.color) if batch else prod.color,
                batch_date_bs=batch.date_bs if batch else None,
            )
        )
    return items


def _safe_resolve_image_path(base_dir: str, file_name: str) -> str:
    """
    Prevents directory traversal (e.g., ../../etc/passwd or absolute path escape)
    by ensuring the canonical resolved path strictly resides inside base_dir.
    """
    canonical_base = os.path.realpath(base_dir)
    safe_name = os.path.basename(file_name)
    resolved = os.path.realpath(os.path.join(canonical_base, safe_name))
    if os.path.commonpath([canonical_base, resolved]) != canonical_base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal path traversal attempt detected"
        )
    return resolved


@router.get("/images/{image_id}/download")
def download_product_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stream or download product image file with multi-tenant scoping and path traversal defense.
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

    file_path = _safe_resolve_image_path(UPLOAD_DIR, image.file_name)
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
    Delete a product image reference and its file from disk. Enforces editor role and path traversal defense.
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

    file_path = _safe_resolve_image_path(UPLOAD_DIR, image.file_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.delete(image)
    db.commit()
    return None
