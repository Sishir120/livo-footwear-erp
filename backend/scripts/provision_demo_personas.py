"""
LIVO Footwear ERP — Staging Synthetic Demo Persona Provisioning CLI
===================================================================
A narrowly scoped, operator-invoked tool for provisioning synthetic demo accounts
for controlled cloud demonstrations without relying on startup ambient hooks or
loosening production allowlists.

Safeguards:
1. Strict Production Refusal:
   - Refuses execution if ENVIRONMENT is 'production' or 'prod'.
   - Refuses execution if database host or name contains production indicators
     ('prod', 'production', 'live', 'client_master').
2. Explicit Database Confirmation:
   - Requires --confirm-target-db matching the exact database name from DATABASE_URL.
3. Account Preservation (No Overwrite):
   - Never resets passwords, reactivates disabled users, or changes roles of existing accounts.
4. No Credential Leakage:
   - Does not log credentials to persistent application loggers.
5. Deterministic Exit Codes:
   - Exits 0 on successful provisioning or clean no-op.
   - Exits 1 on refusal, mismatch, or error.
"""

import sys
import os
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.core.security import get_password_hash

logger = logging.getLogger("livo_erp.provisioning")

PROD_IDENTIFIERS = {"prod", "production", "live", "client_master", "client_live", "primary", "master"}
PROD_ENV_ALIASES = {"production", "prod", "live", "client_prod", "prd"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "staging-postgres", "postgres", "test-db"}

def extract_db_name(db_url: str) -> str:
    """Extracts database name from SQLite or PostgreSQL connection URL."""
    if not db_url or not isinstance(db_url, str):
        return ""
    if db_url.startswith("sqlite"):
        path_str = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not path_str or path_str == ":memory:":
            return ":memory:"
        return Path(path_str).name
    try:
        parsed = urlparse(db_url)
        path = parsed.path.lstrip("/").split("?")[0]
        return path if path else ""
    except Exception:
        return ""

def extract_db_host(db_url: str) -> str:
    """Extracts database hostname from connection URL if applicable."""
    if not db_url or db_url.startswith("sqlite"):
        return "localhost"
    try:
        parsed = urlparse(db_url)
        return (parsed.hostname or "").lower()
    except Exception:
        return ""

def sanitize_db_url_for_display(db_url: str) -> str:
    """Masks database passwords for display."""
    if not db_url:
        return "[empty]"
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)

def is_production_database(db_url: str) -> bool:
    """Analyzes database URL and environment for production markers."""
    # Check Settings and env aliases
    env = (settings.ENVIRONMENT or "").strip().lower()
    if env in PROD_ENV_ALIASES or settings.is_production:
        return True
    
    for env_var in ("ENV", "APP_ENV", "STAGE"):
        val = os.getenv(env_var, "").strip().lower()
        if val in PROD_ENV_ALIASES:
            return True

    if not db_url:
        return True  # Fail closed on empty URL

    db_name = extract_db_name(db_url).lower()
    for marker in PROD_IDENTIFIERS:
        if marker in db_name:
            return True

    host = extract_db_host(db_url)
    for marker in PROD_IDENTIFIERS:
        if marker in host:
            return True

    return False

def provision_demo_personas(
    confirm_db: str, 
    confirm_host: str = None, 
    db_session = None, 
    db_url_override: str = None
) -> Dict[str, Any]:
    db_url = db_url_override if db_url_override is not None else settings.DATABASE_URL
    display_url = sanitize_db_url_for_display(db_url)

    # Fail closed on missing or malformed database URL
    if not db_url or not isinstance(db_url, str):
        error_msg = "[REFUSAL] Missing or malformed DATABASE_URL. Target database cannot be determined."
        print(error_msg, file=sys.stderr)
        return {"status": "rejected", "reason": "malformed_database_configuration", "detail": error_msg}

    db_name = extract_db_name(db_url)
    if not db_name:
        error_msg = f"[REFUSAL] Malformed database URL '{display_url}': database name could not be extracted."
        print(error_msg, file=sys.stderr)
        return {"status": "rejected", "reason": "malformed_database_configuration", "detail": error_msg}

    actual_host = extract_db_host(db_url)

    # Safeguard 1: Production refusal
    if is_production_database(db_url):
        error_msg = (
            f"[REFUSAL] Refusing to provision demo accounts: target database '{display_url}' "
            f"or ENVIRONMENT='{settings.ENVIRONMENT}' is identified as production!"
        )
        print(error_msg, file=sys.stderr)
        return {"status": "rejected", "reason": "production_refusal", "detail": error_msg}

    # Safeguard 2: Explicit confirmation of database name
    if not confirm_db or confirm_db.strip().lower() != db_name.strip().lower():
        error_msg = (
            f"[REFUSAL] Target database confirmation mismatch! "
            f"Expected --confirm-target-db '{db_name}', received '{confirm_db}'."
        )
        print(error_msg, file=sys.stderr)
        return {"status": "rejected", "reason": "database_confirmation_mismatch", "detail": error_msg}

    # Safeguard 3: Host confirmation and remote host refusal
    # A matching database name alone is not sufficient if pointing to the wrong or unconfirmed host!
    if confirm_host is not None:
        if confirm_host.strip().lower() != actual_host:
            error_msg = (
                f"[REFUSAL] Target host confirmation mismatch! "
                f"Expected host '{actual_host}', received '{confirm_host}'."
            )
            print(error_msg, file=sys.stderr)
            return {"status": "rejected", "reason": "host_confirmation_mismatch", "detail": error_msg}
    elif actual_host and actual_host not in LOCAL_HOSTS:
        error_msg = (
            f"[REFUSAL] Target database host '{actual_host}' is non-local. "
            f"A matching database name alone is not sufficient proof of a safe target. "
            f"You must supply --confirm-target-host '{actual_host}' to proceed."
        )
        print(error_msg, file=sys.stderr)
        return {"status": "rejected", "reason": "unconfirmed_remote_host", "detail": error_msg}

    print(f"[*] Verified target database identity: '{db_name}' on host '{actual_host}' ({display_url})")

    session_cm = db_session if db_session is not None else SessionLocal()
    # Check if session_cm is already a Session or needs context management
    if hasattr(session_cm, "__enter__"):
        db = session_cm.__enter__()
        should_close = True
    else:
        db = session_cm
        should_close = False

    try:
        company = db.query(Company).filter(Company.code == "LIVO").first()
        if not company:
            error_msg = "[ERROR] Base tenant company 'LIVO' not found. Run database migrations first."
            print(error_msg, file=sys.stderr)
            return {"status": "failed", "reason": "missing_base_company", "detail": error_msg}

        personas = [
            {
                "username": "admin_demo",
                "name": "LIVO System Administrator",
                "email": "admin@livogroup.com",
                "role": "admin",
                "default_pass": "LivoAdmin2026!"
            },
            {
                "username": "viewer_demo",
                "name": "LIVO Compliance Auditor",
                "email": "auditor@livogroup.com",
                "role": "viewer",
                "default_pass": "LivoViewer2026!"
            },
            {
                "username": "editor_admin",
                "name": "Main Factory Editor",
                "email": "editor@livogroup.com",
                "role": "editor",
                "default_pass": "LivoEditor2026!"
            },
            {
                "username": "viewer_user",
                "name": "Management Viewer",
                "email": "viewer@livogroup.com",
                "role": "viewer",
                "default_pass": "LivoViewer2026!"
            }
        ]

        created_users: List[str] = []
        preserved_users: List[str] = []

        for p in personas:
            existing = db.query(User).filter(User.username == p["username"]).first()
            if existing:
                # Absolute preservation: never modify existing user, role, or password
                preserved_users.append(p["username"])
                continue

            user = User(
                company_id=company.id,
                name=p["name"],
                username=p["username"],
                email=p["email"],
                password_hash=get_password_hash(p["default_pass"]),
                role=p["role"],
                active=True
            )
            db.add(user)
            created_users.append(p["username"])

        db.commit()

        print(f"[SUCCESS] Synthetic demo persona provisioning completed for company '{company.name}'.")
        print(f"          Newly created accounts: {created_users}")
        print(f"          Preserved existing accounts: {preserved_users}")

        return {
            "status": "success",
            "database": db_name,
            "host": actual_host,
            "created_users": created_users,
            "preserved_users": preserved_users
        }
    except Exception as e:
        db.rollback()
        error_msg = f"[ERROR] Provisioning failed due to database error: {e}"
        print(error_msg, file=sys.stderr)
        return {"status": "failed", "reason": "db_exception", "detail": str(e)}
    finally:
        if should_close:
            session_cm.__exit__(None, None, None)


def main():
    parser = argparse.ArgumentParser(description="LIVO ERP Synthetic Demo Persona Provisioning")
    parser.add_argument(
        "--confirm-target-db",
        required=True,
        help="Explicit name of target database (e.g., 'livo_demo' or 'livo_dev.db') to prevent accidental target execution."
    )
    parser.add_argument(
        "--confirm-target-host",
        required=False,
        default=None,
        help="Explicit hostname of target database (required if target database host is non-local)."
    )
    args = parser.parse_args()

    result = provision_demo_personas(args.confirm_target_db, args.confirm_target_host)
    if result["status"] != "success":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
