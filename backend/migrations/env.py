"""
Alembic environment configuration for LIVO GROUP ERP.

Loads SECRET_KEY and DATABASE_URL from .env (via python-dotenv or os.environ)
before importing app settings so the startup validation in config.py passes.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure the app package is importable from the migrations/ subdirectory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env early so SECRET_KEY validation in config.py passes during migration
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; rely on environment variables set externally

# Set a migration-time placeholder if SECRET_KEY still missing
# (migrations don't need JWT signing — they only need DB access)
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "alembic-migration-placeholder-not-for-runtime"

from app.db.session import Base  # noqa: E402
import app.models  # noqa: E402, F401  — registers all models with Base

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Prefer -x db_url=..., then DATABASE_URL env var, then alembic.ini."""
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args and "db_url" in x_args:
        return x_args["db_url"]
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
