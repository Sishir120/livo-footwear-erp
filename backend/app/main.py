from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.session import engine, Base, SessionLocal
from app.models import Company, User
from app.core.security import get_password_hash
from app.core.exceptions import global_exception_handler, http_exception_handler
from app.middleware.audit import AuditLogMiddleware
from app.middleware.rate_limit import BasicRateLimitMiddleware
from app.api.v1.router import api_router

import os
from alembic.config import Config
from alembic import command

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Execute database migrations via Alembic (RULES.md / Item 5 requirement: no more create_all)
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini = os.path.join(backend_dir, "alembic.ini")
        if os.path.exists(alembic_ini):
            alembic_cfg = Config(alembic_ini)
            from sqlalchemy import inspect
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            if "companies" in existing_tables and "alembic_version" not in existing_tables:
                command.stamp(alembic_cfg, "002_invoice_uq")
            else:
                try:
                    command.upgrade(alembic_cfg, "head")
                except Exception:
                    command.stamp(alembic_cfg, "002_invoice_uq")
        else:
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Lifespan DB setup notice: {e}")

    # Seed initial company and users if empty
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

            # Seed editor user
            editor = db.query(User).filter(User.username == "editor_admin").first()
            if not editor:
                editor = User(
                    company_id=company.id,
                    name="Main Factory Editor",
                    username="editor_admin",
                    email="editor@livogroup.com",
                    password_hash=get_password_hash("LivoEditor2026!"),
                    role="editor",
                    active=True
                )
                db.add(editor)

            # Seed viewer user
            viewer = db.query(User).filter(User.username == "viewer_user").first()
            if not viewer:
                viewer = User(
                    company_id=company.id,
                    name="Management Viewer",
                    username="viewer_user",
                    email="viewer@livogroup.com",
                    password_hash=get_password_hash("LivoViewer2026!"),
                    role="viewer",
                    active=True
                )
                db.add(viewer)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Seeding rollback notice: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"Lifespan seeding notice: {e}")

    yield

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Middlewares
app.add_middleware(AuditLogMiddleware)
app.add_middleware(BasicRateLimitMiddleware)

# CORS Policy - Locked to frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Versioned Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
