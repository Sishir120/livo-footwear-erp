import logging
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.company import Company
from app.core.security import get_password_hash

logger = logging.getLogger("livo_erp.security")

ALLOWED_NON_PROD_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}

def seed_demo_users_if_enabled(db: Session, company: Company) -> dict:
    """
    Explicit, opt-in demo user provisioning for local development or controlled testing only.
    
    Safeguards:
    1. Disabled by default: ENABLE_DEMO_SEEDING must be explicitly set to 'true'.
    2. Fail closed on ambiguous environment: ENVIRONMENT must be positively in ALLOWED_NON_PROD_ENVIRONMENTS.
    3. Production prohibition: Strictly refuses to run if ENVIRONMENT is 'production', 'prod', or any unknown env.
    4. Account preservation: Never modifies, reactivates, or resets existing user records.
    5. Audit logging: Emits explicit security warnings whenever demo seeding runs.
    """
    if not settings.ENABLE_DEMO_SEEDING:
        logger.info("[SEC-01] Demo account seeding is disabled by default (ENABLE_DEMO_SEEDING=false). Skipping demo provisioning.")
        return {"status": "skipped", "reason": "disabled_by_default"}

    env_clean = (settings.ENVIRONMENT or "").strip().lower()

    if settings.is_production or env_clean not in ALLOWED_NON_PROD_ENVIRONMENTS:
        reason = "production_mode_refusal" if settings.is_production else "ambiguous_environment_refusal"
        logger.critical(
            "[SEC-01 ALERT] Demo account seeding was requested (ENABLE_DEMO_SEEDING=true) but ENVIRONMENT='%s' "
            "is not positively identified as non-production. Refusing to seed demo credentials (fail closed)!",
            settings.ENVIRONMENT
        )
        return {"status": "rejected", "reason": reason}

    logger.warning(
        "[SEC-01 NOTICE] ENABLE_DEMO_SEEDING=true in '%s' mode. Provisioning demo persona accounts for testing...",
        settings.ENVIRONMENT
    )

    seeded_usernames = []

    # 1. Executive Admin Persona
    admin_demo = db.query(User).filter(User.username == "admin_demo").first()
    if not admin_demo:
        admin_demo = User(
            company_id=company.id,
            name="LIVO System Administrator",
            username="admin_demo",
            email="admin@livogroup.com",
            password_hash=get_password_hash("LivoAdmin2026!"),
            role="admin",
            active=True
        )
        db.add(admin_demo)
        seeded_usernames.append("admin_demo")

    # 2. Compliance Auditor Persona (Viewer)
    viewer_demo = db.query(User).filter(User.username == "viewer_demo").first()
    if not viewer_demo:
        viewer_demo = User(
            company_id=company.id,
            name="LIVO Compliance Auditor",
            username="viewer_demo",
            email="auditor@livogroup.com",
            password_hash=get_password_hash("LivoViewer2026!"),
            role="viewer",
            active=True
        )
        db.add(viewer_demo)
        seeded_usernames.append("viewer_demo")

    # 3. Factory Floor Editor Persona
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
        seeded_usernames.append("editor_admin")

    # 4. Management Viewer Persona
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
        seeded_usernames.append("viewer_user")

    db.commit()
    return {"status": "seeded", "seeded_users": seeded_usernames}
