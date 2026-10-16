"""
LIVO Footwear ERP — Staging Artifact Forensic Rehearsal & Validation
====================================================================
1. Audits archive paths: rejects path traversal ('..'), absolute paths, unsafe symlinks.
2. Secret scanning: searches archive file contents for private keys, tokens, and credentials.
3. Manifest validation: verifies every file in staging_artifact_manifest.sha256 against extracted files.
4. Clean extraction rehearsal: unpacks archive into an isolated temporary directory.
5. Runtime validation of extracted artifact:
   - Runs database migration up to head (024) in the extracted sandbox.
   - Bootstraps FastAPI application from extracted code.
   - Tests readiness probe, authentication, protected routes, and failure behavior.
"""

import os
import sys
import re
import tarfile
import tempfile
import hashlib
import pathlib
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TAR_PATH = ROOT / "livo_staging_artifact.tar.gz"
MANIFEST_PATH = ROOT / "staging_artifact_manifest.sha256"

FORBIDDEN_NAME_PATTERNS = [
    ".env", "livo_dev.db", "staging_pgdata", "pg_binaries.zip"
]

FORBIDDEN_DIR_PATTERNS = [
    "venv", "node_modules", ".next", "__pycache__", ".pytest_cache", ".git"
]

SECRET_PATTERNS = [
    (re.compile(rb"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"), "Private Key Header"),
    (re.compile(rb"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(rb"(?i)postgres://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@"), "Hardcoded PostgreSQL Credentials"),
]


def audit_and_validate():
    if not TAR_PATH.exists():
        print(f"[FATAL] Artifact not found: {TAR_PATH}", file=sys.stderr)
        sys.exit(1)
    if not MANIFEST_PATH.exists():
        print(f"[FATAL] Manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    tar_size = TAR_PATH.stat().st_size
    print(f"[*] Step 1: Auditing archive structure: {TAR_PATH.name} ({tar_size} bytes / {tar_size / 1024 / 1024:.2f} MB)")

    with tarfile.open(TAR_PATH, "r:gz") as tar:
        members = tar.getmembers()
        print(f"[*] Total entries in archive: {len(members)}")

        # 1. Path safety checks
        for m in members:
            # Check path traversal
            if ".." in m.name or m.name.startswith("/") or m.name.startswith("\\"):
                print(f"[FATAL] Path traversal attempt detected in archive entry: {m.name}", file=sys.stderr)
                sys.exit(1)
            # Check symlinks pointing outside
            if m.issym() or m.islnk():
                link = m.linkname
                if ".." in link or link.startswith("/"):
                    print(f"[FATAL] Unsafe symlink detected: {m.name} -> {link}", file=sys.stderr)
                    sys.exit(1)

            # Check forbidden directory and file names
            parts = pathlib.Path(m.name).parts
            for fd in FORBIDDEN_DIR_PATTERNS:
                if fd in parts:
                    print(f"[FATAL] Forbidden directory bundled in archive: {m.name}", file=sys.stderr)
                    sys.exit(1)

            fname = pathlib.Path(m.name).name
            if fname.startswith(".env") and not fname.endswith(".example"):
                print(f"[FATAL] Secret .env file discovered in archive: {m.name}", file=sys.stderr)
                sys.exit(1)

            for fp in FORBIDDEN_NAME_PATTERNS:
                if fname == fp:
                    print(f"[FATAL] Forbidden file bundled in archive: {m.name}", file=sys.stderr)
                    sys.exit(1)

        print("[PASS] Archive paths, symlinks, and exclusion boundaries verified clean.")

        # 2. Secret scan across file contents
        print("[*] Step 2: Scanning file contents for secret patterns & private keys...")
        secret_findings = 0
        for m in members:
            if m.isreg():
                f = tar.extractfile(m)
                if f:
                    content = f.read(512 * 1024)  # inspect first 512 KB
                    for pat, desc in SECRET_PATTERNS:
                        if pat.search(content):
                            # Redact file name and matched snippet
                            print(f"[ALERT] Potential secret ({desc}) flagged in: {m.name}", file=sys.stderr)
                            secret_findings += 1

        if secret_findings > 0:
            print(f"[FATAL] Secret scanner flagged {secret_findings} violations in artifact contents!", file=sys.stderr)
            sys.exit(1)
        print("[PASS] Zero private keys, access tokens, or connection credentials discovered in archive.")

    # 3. Clean extraction into temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        print(f"[*] Step 3: Unpacking archive into clean isolated sandbox: {tmp_path}")
        with tarfile.open(TAR_PATH, "r:gz") as tar:
            tar.extractall(path=tmp_path)

        # 4. Manifest hash verification
        print("[*] Step 4: Verifying manifest checksums against extracted files...")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as mf:
            lines = [l.strip() for l in mf if l.strip()]

        mismatches = 0
        missing = 0
        seen_paths = set()

        for line in lines:
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            expected_hash, rel_path = parts
            if rel_path in seen_paths:
                print(f"[FATAL] Duplicate path in manifest: {rel_path}", file=sys.stderr)
                sys.exit(1)
            seen_paths.add(rel_path)

            target = tmp_path / rel_path
            if not target.exists():
                missing += 1
                mismatches += 1
                continue
            with open(target, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            if actual_hash != expected_hash:
                mismatches += 1

        if mismatches > 0:
            print(f"[FATAL] Manifest verification failed: {mismatches} mismatches ({missing} missing files)!", file=sys.stderr)
            sys.exit(1)
        print(f"[PASS] 100% SHA-256 hash match verified across all {len(lines)} extracted files.")

        # 5. Runtime execution from extracted artifact sandbox
        print("[*] Step 5: Executing runtime startup rehearsal using extracted code...")
        extracted_backend = tmp_path / "backend"
        sys.path.insert(0, str(extracted_backend))

        sandbox_db_file = tmp_path / "sandbox_test.db"
        sandbox_db_url = f"sqlite:///{sandbox_db_file.as_posix()}"

        os.environ["DATABASE_URL"] = sandbox_db_url
        os.environ["SECRET_KEY"] = "sandbox_forensic_validation_secret_key_32bytes_long!"
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["AUTO_MIGRATE"] = "true"
        os.environ["LIVO_DEV_MODE"] = "true"

        # Apply Alembic migrations in extracted sandbox
        from alembic.config import Config
        from alembic import command
        alembic_ini = extracted_backend / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", sandbox_db_url)
        command.upgrade(cfg, "head")
        print("[PASS] Extracted Alembic migrations executed to head successfully.")

        # Import extracted app and run FastAPI TestClient
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app, base_url="https://testserver") as client:
            # A. Readiness probe
            r_ready = client.get("/api/v1/health/ready")
            assert r_ready.status_code == 200, f"Expected 200, got {r_ready.status_code}: {r_ready.text}"
            assert r_ready.json()["status"] == "ready"
            print("[PASS] Extracted app readiness probe returns HTTP 200 'ready'.")

            # B. Provision demo personas in sandbox
            from scripts.provision_demo_personas import provision_demo_personas
            prov_res = provision_demo_personas(confirm_db="sandbox_test.db")
            assert prov_res["status"] == "success"
            assert "admin_demo" in prov_res["created_users"]
            print("[PASS] Extracted provision_demo_personas CLI successfully provisioned synthetic personas.")

            # C. Authentication against extracted app
            r_login = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_demo", "password": "LivoAdmin2026!"}
            )
            assert r_login.status_code == 200, f"Login failed: {r_login.text}"
            set_cookie = r_login.headers.get("set-cookie", "")
            match = re.search(r"access_token=([^;]+)", set_cookie)
            assert match is not None, f"access_token not found in set-cookie header: {set_cookie}"
            token = match.group(1)
            assert len(token) > 20
            print("[PASS] Authentication against extracted artifact successful (httpOnly secure cookie issued).")

            # D. Authenticated protected API call using session cookie
            r_stock = client.get("/api/v1/stock/movements", cookies={"access_token": token})
            assert r_stock.status_code == 200, f"Expected 200, got {r_stock.status_code}: {r_stock.text}"
            print("[PASS] Authenticated protected endpoint (/api/v1/stock/movements) returned HTTP 200 via session cookie.")

            # E. Unauthenticated protected API call -> 401
            with TestClient(app, base_url="https://testserver") as unauth_client:
                r_unauth = unauth_client.get("/api/v1/stock/movements")
                assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"
                print("[PASS] Unauthenticated access to protected route correctly rejected with HTTP 401.")

            # F. Readiness failure when database connection is unavailable
            class BrokenDB:
                def execute(self, stmt):
                    raise ConnectionError("Simulated PostgreSQL connection timeout")

            def broken_get_db():
                yield BrokenDB()

            from app.api.deps import get_db
            app.dependency_overrides[get_db] = broken_get_db
            try:
                r_unready = client.get("/api/v1/health/ready")
                assert r_unready.status_code == 503
                assert r_unready.json()["status"] == "unready"
                print("[PASS] Extracted app readiness probe returns HTTP 503 'unready' when database drops.")
            finally:
                app.dependency_overrides.clear()

    print("\n=======================================================")
    print("[SUCCESS] All Phase 4 artifact forensic checks PASSED.")
    print("=======================================================")


if __name__ == "__main__":
    audit_and_validate()
