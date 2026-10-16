"""
LIVO Footwear ERP — Staging Artifact Packager
============================================
Packages the verified local workspace (including all 34 tracked modifications,
new migrations, test suites, and documentation) into a reproducible tarball with
a cryptographic SHA-256 manifest.

Excludes:
- Secret material (.env, .env.*)
- Virtual environments (venv/, env/)
- Node modules (node_modules/)
- Build caches (.next/, __pycache__/, .pytest_cache/)
- Local databases and journals (*.db, *.db-wal, *.db-shm, staging_pgdata/)
- Physical backup dumps (backups/*.sql, backups/*.db, backups/*.tar.gz)
- Binaries and scratch files (pg_binaries.zip, scratch/)
"""

import os
import tarfile
import hashlib
import pathlib
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND_DIR.parent

OUTPUT_TAR = ROOT / "livo_staging_artifact.tar.gz"
OUTPUT_MANIFEST = ROOT / "staging_artifact_manifest.sha256"

EXCLUDE_DIRS = {
    ".git", "venv", "node_modules", ".next", "__pycache__", 
    ".pytest_cache", "staging_pgdata", "scratch", ".gemini", "_unscoped"
}

EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".shm", ".wal", ".tmp", ".log", ".db", ".sqlite", ".sqlite3"}
EXCLUDE_FILES = {
    "livo_dev.db", "pg_binaries.zip", 
    "livo_staging_artifact.tar.gz", "staging_artifact_manifest.sha256"
}

def is_included(path: pathlib.Path, rel_path: pathlib.Path) -> bool:
    parts = rel_path.parts
    # Exclude directories
    if any(ex in parts for ex in EXCLUDE_DIRS):
        return False
    # Exclude any .env file anywhere in the workspace
    if path.name.startswith(".env"):
        return False
    # Exclude extensions
    if path.suffix in EXCLUDE_EXTS:
        return False
    # Exclude secret keys / certs if any
    if path.suffix in {".key", ".pem", ".pfx", ".p12"}:
        return False
    # Exclude specific files
    if path.name in EXCLUDE_FILES:
        return False
    # Exclude physical backup dumps and archives from backups/
    if "backups" in parts and path.suffix in {".sql", ".db", ".dump", ".gz", ".tar.gz"}:
        return False
    # Exclude media recordings and temp files
    if path.suffix in {".webp", ".mp4", ".mov"}:
        return False
    return True

def package():
    print(f"Scanning workspace root: {ROOT}")
    file_list = []
    
    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT)
            if is_included(p, rel):
                file_list.append((p, rel))

    file_list.sort(key=lambda x: x[1].as_posix())
    print(f"Discovered {len(file_list)} packageable files.")

    manifest_lines = []
    with tarfile.open(OUTPUT_TAR, "w:gz") as tar:
        for full_path, rel_path in file_list:
            tar.add(full_path, arcname=rel_path.as_posix())
            with open(full_path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            manifest_lines.append(f"{digest}  {rel_path.as_posix()}\n")

    with open(OUTPUT_MANIFEST, "w", encoding="utf-8") as mf:
        mf.writelines(manifest_lines)

    tar_size = OUTPUT_TAR.stat().st_size
    print(f"[SUCCESS] Artifact created: {OUTPUT_TAR.name} ({tar_size} bytes / {tar_size / 1024 / 1024:.2f} MB)")
    print(f"[SUCCESS] Manifest created: {OUTPUT_MANIFEST.name} ({len(manifest_lines)} entries)")

if __name__ == "__main__":
    package()
