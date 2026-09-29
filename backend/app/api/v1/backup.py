from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.services.backup_service import run_database_backup, get_latest_backup_status

router = APIRouter(prefix="/backup", tags=["Backup"])

@router.get("/status")
def get_backup_status(current_user: User = Depends(get_current_user)):
    """Returns the latest database backup status for display in Settings screen."""
    return get_latest_backup_status()

@router.post("/run")
def trigger_backup(current_user: User = Depends(require_admin)):
    """Triggers an immediate database backup (pg_dump + cloud upload if configured)."""
    result = run_database_backup()
    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error_message", "Database backup failed.")
        )
    return result
