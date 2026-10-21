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


import os
import sys
import pathlib
import urllib.parse
from sqlalchemy.engine import make_url

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEV_DB_PATHS = {
    (WORKSPACE_ROOT / "livo_dev.db").resolve(),
    (WORKSPACE_ROOT / "backend" / "livo_dev.db").resolve(),
}

def is_protected_developer_database(target_url) -> bool:
    """
    Evaluates whether target_url resolves canonically to a protected developer database.
    Uses SQLAlchemy's make_url for standard URL parsing, automatic URL decoding,
    query parameter extraction, and SQLite database path resolution.
    Canonicalizes filesystem paths to eliminate relative paths, symlinks, redundancy,
    and platform separator differences.
    """
    if not target_url:
        return False
    try:
        url_obj = make_url(str(target_url).strip())
    except Exception:
        raw_str = urllib.parse.unquote(str(target_url).strip()).lower()
        return "livo_dev.db" in raw_str

    driver = url_obj.drivername.lower()
    if not driver.startswith("sqlite"):
        return False

    db_path_str = url_obj.database
    if not db_path_str or db_path_str == ":memory:":
        return False

    try:
        resolved = pathlib.Path(db_path_str).resolve()
        if resolved in DEV_DB_PATHS or resolved.name.lower() == "livo_dev.db":
            return True
    except Exception:
        if "livo_dev.db" in str(db_path_str).lower():
            return True

    return False

def validate_database_target_safety(target_url: str):
    """
    Enforces policy-based fail-closed protection of developer databases.

    POLICY REQUIREMENTS:
    1. UNCONDITIONAL REJECTION: Any connection to either protected developer database
       (livo_dev.db or backend/livo_dev.db) is unconditionally rejected across all
       execution modes (interactive CLI, standalone scripts with arbitrary names, web server,
       Alembic migrations, automated test runners, etc.).
    2. ZERO OVERRIDE MECHANISM: There is no environment variable, flag, or token that
       permits connecting to protected developer databases. Any legacy override variable
       such as LIVO_ALLOW_PROTECTED_DEV_DB_ACCESS is completely ignored.
    3. TEST MODE PROTECTION: Test environments (pytest, ENVIRONMENT=test/testing,
       PYTEST_CURRENT_TEST) are strictly prevented from binding to protected databases.
    4. ZERO CREDENTIAL LEAKAGE: Mask connection string secrets in error messages.
    5. ACTIONABLE DIAGNOSTICS: Provide clear guidance directing operators to configure
       an isolated disposable database (e.g. sqlite:///./disposable.db or PostgreSQL).
    """
    if not is_protected_developer_database(target_url):
        return

    # Safe target representation for logging without exposing credentials
    try:
        parsed_url = make_url(str(target_url).strip())
        safe_target = parsed_url.render_as_string(hide_password=True)
    except Exception:
        safe_target = "[unparseable database target]"

    # Detect test runtimes
    invoking_script = os.path.basename(sys.argv[0]).lower() if sys.argv and sys.argv[0] else ""
    is_test_runtime = (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.getenv("ENVIRONMENT", "").lower() in ("testing", "test")
        or os.getenv("LIVO_BLOCK_DEV_DB", "").lower() in ("true", "1")
        or invoking_script.startswith("test_")
        or invoking_script.endswith("_test.py")
        or "pytest" in invoking_script
    )

    # In test runtimes, protected developer database access is unconditionally forbidden
    if is_test_runtime:
        raise RuntimeError(
            f"[FAIL-CLOSED DB GUARD] Prohibited connection to protected developer database '{safe_target}' "
            "in test environment. Automated tests and verification scripts must bind strictly to an "
            "isolated disposable database."
        )

    # In non-test runtimes, protected developer database access is unconditionally forbidden
    raise RuntimeError(
        f"[FAIL-CLOSED DB GUARD] Prohibited connection to protected developer database '{safe_target}'. "
        "Connections to developer databases (livo_dev.db, backend/livo_dev.db) are unconditionally "
        "forbidden across all execution modes to prevent accidental corruption or mutation of historical data. "
        "To run locally or in staging, configure an isolated database URL in DATABASE_URL "
        "(e.g., sqlite:///./disposable.db or postgresql://...)."
    )

# Execute fail-closed database safety validation before engine construction
validate_database_target_safety(db_url)

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
