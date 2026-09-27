import os
import zipfile
import io
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db, get_current_user
from app.config import settings
from app.models.user import User

router = APIRouter(tags=["Health & System"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",  # [L-03 FIX] Harmonized to 'healthy'
        "version": settings.VERSION,
        "database": db_status,
        "app_name": settings.PROJECT_NAME
    }

@router.get("/diagnostics/download")
def download_diagnostics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generates a diagnostics ZIP bundle containing logs, system status, and DB self-check.
    Mandated by RULES.md §2.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Write info json
        info_content = f"""App Name: {settings.PROJECT_NAME}
Version: {settings.VERSION}
Database Status: {db_status}
Requested By User: {current_user.name} ({current_user.username})
Role: {current_user.role}
Company ID: {current_user.company_id}
"""
        zip_file.writestr("system_info.txt", info_content)
        
        # Include log file if exists
        log_path = os.path.join("logs", "livo_erp.log")
        if os.path.exists(log_path):
            zip_file.write(log_path, arcname="livo_erp.log")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=livo_diagnostics.zip"}
    )
