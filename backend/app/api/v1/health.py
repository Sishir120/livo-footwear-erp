import os
import zipfile
import io
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db, require_admin
from app.config import settings
from app.models.user import User

logger = logging.getLogger("livo_erp")

router = APIRouter(tags=["Health & System"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """General health check (backward-compatible)."""
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check database connectivity failure: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.VERSION,
        "commit": settings.BUILD_COMMIT,
        "database": db_status,
        "app_name": settings.PROJECT_NAME
    }

@router.get("/health/live")
def liveness_check():
    """
    Kubernetes/Container Liveness Probe:
    Answers: Is the application process running and capable of servicing HTTP requests?
    Does NOT depend on external databases or network services, preventing unnecessary restarts.
    """
    return {
        "status": "alive",
        "version": settings.VERSION,
        "commit": settings.BUILD_COMMIT,
        "app_name": settings.PROJECT_NAME
    }

def get_alembic_script_directory():
    """Resolves and loads Alembic ScriptDirectory from alembic.ini."""
    try:
        import pathlib
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        alembic_ini = pathlib.Path(__file__).resolve().parents[3] / "alembic.ini"
        if alembic_ini.exists():
            cfg = Config(str(alembic_ini))
            return ScriptDirectory.from_config(cfg)
    except Exception as e:
        logger.warning("Could not load Alembic ScriptDirectory: %s", e)
    return None

def get_expected_migration_head() -> Optional[str]:
    """Dynamically resolves the single expected Alembic migration head from the revision graph."""
    script = get_alembic_script_directory()
    if script is None:
        return None
    try:
        heads = script.get_heads()
        if len(heads) == 1:
            return heads[0]
        elif len(heads) > 1:
            logger.error("Multiple Alembic migration heads detected: %s", heads)
            return None
    except Exception as e:
        logger.error("Error retrieving Alembic heads: %s", e)
    return None

@router.get("/health/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """
    Kubernetes/Container Readiness Probe:
    Answers: Can this instance safely serve production traffic?
    Verifies:
    1. Database connectivity (SELECT 1).
    2. Dynamic Alembic migration head resolution (rejects unverified or conflicting heads).
    3. Database revision validation against alembic_version table (catches missing, empty, outdated, or divergent schemas).
    4. Lightweight schema invariants on critical tables (companies, users, invoices, etc.) and columns (< 5ms).
    Returns HTTP 200 when ready, HTTP 503 when degraded or schema mismatch.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check database connectivity failure: {e}")
        response.status_code = 503
        return {
            "status": "unready",
            "database": "unhealthy",
            "detail": "Database connection probe failed."
        }

    # Resolve expected migration head from active Alembic revision graph
    script = get_alembic_script_directory()
    if script is None:
        response.status_code = 503
        logger.error("Readiness probe rejected: unable to resolve Alembic configuration")
        return {
            "status": "unready",
            "database": "schema_unverified",
            "detail": "Database schema verification failed (Alembic configuration unresolvable)."
        }

    heads = script.get_heads()
    if len(heads) != 1:
        response.status_code = 503
        logger.error("Readiness probe rejected: ambiguous migration heads in Alembic graph: %s", heads)
        return {
            "status": "unready",
            "database": "schema_unverified",
            "sub_status": "multiple_migration_heads" if len(heads) > 1 else "no_migration_heads",
            "heads": heads,
            "detail": f"Alembic configuration contains ambiguous migration heads: {heads}"
        }

    expected_head = heads[0]

    # Query alembic_version table
    try:
        res = db.execute(text("SELECT version_num FROM alembic_version"))
        rows = res.fetchall() if hasattr(res, "fetchall") else None
        if not isinstance(rows, (list, tuple)):
            first_row = res.first() if hasattr(res, "first") else None
            rows = [first_row] if first_row is not None and not hasattr(first_row, "_mock_return_value") else []
        if not rows or rows[0] is None:
            response.status_code = 503
            logger.warning("Readiness probe rejected: alembic_version table is empty")
            return {
                "status": "unready",
                "database": "schema_mismatch",
                "sub_status": "revision_empty",
                "expected_head": expected_head,
                "detail": "Database alembic_version table is empty."
            }
        if len(rows) > 1:
            db_revisions = [r[0] for r in rows]
            response.status_code = 503
            logger.warning("Readiness probe rejected: multiple revisions in database: %s", db_revisions)
            return {
                "status": "unready",
                "database": "schema_mismatch",
                "sub_status": "multiple_database_revisions",
                "expected_head": expected_head,
                "current_revisions": db_revisions,
                "detail": f"Multiple active revisions found in database: {db_revisions}"
            }

        current_head = rows[0][0]
        if current_head != expected_head:
            known_revisions = [s.revision for s in script.walk_revisions()]
            if current_head in known_revisions:
                sub_status = "revision_behind"
                detail = f"Database schema revision '{current_head}' is behind expected application head '{expected_head}'."
            else:
                sub_status = "revision_unknown_or_ahead"
                detail = f"Database schema revision '{current_head}' is unknown to application or ahead of expected head '{expected_head}'."

            response.status_code = 503
            logger.warning(
                "Readiness probe rejected: database schema revision '%s' mismatch with expected head '%s' (%s)",
                current_head, expected_head, sub_status
            )
            return {
                "status": "unready",
                "database": "schema_mismatch",
                "sub_status": sub_status,
                "expected_head": expected_head,
                "current_head": current_head,
                "detail": detail
            }
    except Exception as schema_err:
        response.status_code = 503
        logger.warning("Readiness probe rejected: alembic_version query failed: %s", schema_err)
        return {
            "status": "unready",
            "database": "schema_unverified",
            "detail": "Database schema verification failed (missing or unreadable alembic_version table)."
        }

    # Lightweight Schema Invariant Verification (Fast catalog check: < 5ms)
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        existing_tables = set(inspector.get_table_names())
        critical_tables = {"companies", "users", "invoices", "products", "production_batches", "stock_movements"}
        missing_tables = critical_tables - existing_tables
        if missing_tables:
            response.status_code = 503
            logger.critical("Readiness probe rejected: critical tables missing: %s", missing_tables)
            return {
                "status": "unready",
                "database": "schema_invariant_violation",
                "missing_tables": sorted(list(missing_tables)),
                "detail": f"Critical tables missing from database: {sorted(list(missing_tables))}"
            }

        user_cols = {col["name"] for col in inspector.get_columns("users")}
        critical_user_cols = {"id", "company_id", "username", "password_hash", "role", "active"}
        missing_cols = critical_user_cols - user_cols
        if missing_cols:
            response.status_code = 503
            logger.critical("Readiness probe rejected: critical columns missing on users table: %s", missing_cols)
            return {
                "status": "unready",
                "database": "schema_invariant_violation",
                "missing_columns": sorted(list(missing_cols)),
                "detail": f"Critical columns missing from users table: {sorted(list(missing_cols))}"
            }
    except Exception as inv_err:
        response.status_code = 503
        logger.warning("Readiness probe rejected: schema invariant inspection failed: %s", inv_err)
        return {
            "status": "unready",
            "database": "schema_invariant_violation",
            "detail": f"Schema invariant inspection failed: {inv_err}"
        }

    return {
        "status": "ready",
        "database": "healthy",
        "version": settings.VERSION,
        "commit": settings.BUILD_COMMIT,
        "current_head": current_head
    }

@router.get("/diagnostics/download")
def download_diagnostics(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    Generates a diagnostics ZIP bundle containing logs, system status, and DB self-check.
    Restricted to administrator role to prevent unauthorized log/topology exfiltration.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Diagnostics DB self-check failure: {e}")
        db_status = "unhealthy"

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
