from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
elif db_url.startswith("postgresql"):
            # Enforce SSL for all hosted PostgreSQL connections.
            # Local dev (localhost/127.0.0.1) is excluded to avoid certificate hassles.
            # This ensures all production/hosted DB traffic is encrypted in transit
            # without requiring superuser privileges or manual certificate management.
            is_local = any(host in db_url for host in ["localhost", "127.0.0.1", "host.docker.internal"])
            if not is_local:
                        # sslmode=require: encrypted connection mandatory, server certificate
                        # verified by the client's default CA bundle (sufficient for Neon, RDS,
                        # Cloud SQL, and all major managed Postgres providers).
                        connect_args["sslmode"] = "require"


from sqlalchemy import event

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )
else:
    import os
    pool_size = int(os.getenv("DB_POOL_SIZE", "15"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "15"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "10"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True
    )

if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

from app.db.observability import attach_db_observability
attach_db_observability(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        from app.core.locks import release_all_session_locks
        release_all_session_locks(db)
        db.close()
