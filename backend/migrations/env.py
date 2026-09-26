"""
Alembic environment configuration for LIVO GROUP ERP.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
        pass

if not os.getenv("SECRET_KEY"):
        os.environ["SECRET_KEY"] = "alembic-migration-placeholder-not-for-runtime"

from app.db.session import Base
import app.models

config = context.config

if config.config_file_name is not None:
        fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
        """Prefer -x db_url=..., then DATABASE_URL env var, then alembic.ini."""
        x_args = context.get_x_argument(as_dictionary=True)
        if x_args and "db_url" in x_args:
                    url = x_args["db_url"]
else:
        url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))

    if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)

    url = url.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?").replace("?channel_binding=require", "")
    return url


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
    
