from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.session import engine, Base, SessionLocal
from app.models import Company, User, Warehouse
from app.core.security import get_password_hash
from app.core.exceptions import global_exception_handler, http_exception_handler
from app.middleware.audit import AuditLogMiddleware
from app.middleware.rate_limit import BasicRateLimitMiddleware
from app.api.v1.router import api_router

import os
import re
import logging
import threading
from sqlalchemy import text
from alembic.config import Config
from alembic import command
from app.core.demo_seeding import seed_demo_users_if_enabled

logger = logging.getLogger("livo_erp.lifecycle")

_migration_lock = threading.Lock()
MIGRATION_COORDINATION_LOCK_ID = 8877665544332211

def _sanitize_db_error(msg: str) -> str:
    """Masks database passwords in connection strings from logs and exception messages."""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(msg))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Execute database migrations via Alembic if AUTO_MIGRATE is enabled (SEC-02: fail safely on error)
    if settings.AUTO_MIGRATE:
        with _migration_lock:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            alembic_ini = os.path.join(backend_dir, "alembic.ini")
            if os.path.exists(alembic_ini):
                alembic_cfg = Config(alembic_ini)
                alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
                
                # Coordinate concurrent multi-instance deployments via PostgreSQL advisory lock
                pg_conn = None
                is_pg = False
                try:
                    if engine.dialect.name == "postgresql":
                        is_pg = True
                        pg_conn = engine.connect()
                        pg_conn.execute(text(f"SELECT pg_advisory_lock({MIGRATION_COORDINATION_LOCK_ID})"))
                        logger.info("Acquired PostgreSQL migration advisory lock.")
                except Exception as lock_err:
                    logger.warning("Could not acquire PostgreSQL migration advisory lock: %s", _sanitize_db_error(lock_err))

                try:
                    logger.info("Applying database migrations up to head...")
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Database migrations applied successfully.")
                except Exception as e:
                    sanitized = _sanitize_db_error(e)
                    logger.critical("FATAL: Database migration failed during application startup: %s", sanitized, exc_info=True)
                    # CRITICAL (SEC-02): Abort startup immediately. Never serve live traffic on a failed schema!
                    raise RuntimeError(f"Database migration failure: {sanitized}") from None
                finally:
                    if is_pg and pg_conn:
                        try:
                            pg_conn.execute(text(f"SELECT pg_advisory_unlock({MIGRATION_COORDINATION_LOCK_ID})"))
                            pg_conn.close()
                            logger.info("Released PostgreSQL migration advisory lock.")
                        except Exception:
                            pass
            else:
                logger.warning("alembic.ini not found. Falling back to metadata.create_all.")
                Base.metadata.create_all(bind=engine)
    else:
        logger.info("AUTO_MIGRATE=false. Skipping startup migrations (managed via deployment release gate).")

    # Seed initial tenant company and warehouse structure if missing
    try:
        db = SessionLocal()
        try:
            company = db.query(Company).filter(Company.code == "LIVO").first()
            if not company:
                company = Company(
                    name="LIVO GROUP OF INDUSTRIES",
                    code="LIVO",
                    pan_number="600123456",
                    address="Kathmandu, Nepal",
                    phone="+977-1-4000000"
                )
                db.add(company)
                db.commit()
                db.refresh(company)

            # Seed default main finished goods warehouse
            warehouse = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.code == "WH-MAIN").first()
            if not warehouse:
                warehouse = Warehouse(
                    company_id=company.id,
                    name="Main Finished Warehouse",
                    code="WH-MAIN",
                    location="Factory Premises, Birgunj",
                    is_active=True
                )
                db.add(warehouse)
                db.commit()

            # SEC-01: Demo accounts are strictly opt-in and forbidden in production
            seed_demo_users_if_enabled(db, company)

        except Exception as e:
            db.rollback()
            logger.error(f"Tenant initialization notice: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Lifespan tenant setup notice: {e}")

    yield

    # Graceful Shutdown Handler
    try:
        logger.info("Executing graceful application shutdown: disposing DB engine and flushing logs.")
        engine.dispose()
        for handler in logger.handlers:
            handler.flush()
    except Exception as e:
        print(f"Shutdown cleanup notice: {e}")

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Exception handlers
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import validation_exception_handler

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.idempotency import IdempotencyMiddleware

# Middlewares
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(BasicRateLimitMiddleware)

# CORS Policy - Locked to frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Idempotency-Key", "X-Idempotent-Replay"],
)

# Include Versioned Routers & Root Health Probes
from app.api.v1.health import router as health_router
app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
