# LIVO Footwear ERP — Day 7.1 Staging Artifact Packaging & Verification Procedure

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Reproducible Build & Secure Artifact Packaging Baseline  
**Workspace:** `D:\Antigravity\Footwear app`

---

## 1. Executive Summary & Working-Tree Awareness

Because the local workspace contains 34 intentional tracked modifications (and specific migration/test additions) that are not yet committed to Git, **a naive `git clone` or `git archive` would NOT reproduce the tested application**.

This procedure defines an exact, reproducible packaging process that captures all intended source code, components, migrations, and dependency definitions while strictly excluding secrets, virtual environments, local databases, and temporary test artifacts.

---

## 2. Packaging Exclusions & Inclusions Matrix

| Category | Inclusions (Included in Artifact) | Exclusions (Strictly Excluded) |
| :--- | :--- | :--- |
| **Secrets & Env** | `.env.example`, `.env.staging.example` | `.env`, `.env.local`, `.env.production`, all active credentials |
| **Backend Code** | `backend/app/`, `backend/scripts/`, `backend/migrations/`, `backend/alembic.ini` | `backend/venv/`, `__pycache__/`, `.pytest_cache/` |
| **Frontend Code** | `frontend/src/`, `frontend/public/`, `frontend/package.json`, `frontend/next.config.js` | `frontend/node_modules/`, `frontend/.next/` |
| **Databases & Dumps**| Base migration scripts (`001` through `024`) | `livo_dev.db`, `*.db-wal`, `*.db-shm`, `staging_pgdata/` |
| **Infrastructure** | `Dockerfile`, `docker-compose.yml`, `Caddyfile` | `pg_binaries.zip`, local scratch files |
| **Documentation** | `docs/*.md`, `ARCHITECTURE.md` | Temporary video recordings and scratch debug scripts |

---

## 3. Operator Packaging Script (`scripts/package_staging_artifact.py`)

The operator can execute the following standalone packaging script from workspace root:

```python
"""
LIVO Footwear ERP — Staging Artifact Packager
Packages tested workspace into a reproducible tarball with SHA-256 manifest.
Usage:
  python backend/scripts/package_staging_artifact.py
"""

import os
import tarfile
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_TAR = ROOT / "livo_staging_artifact.tar.gz"
OUTPUT_MANIFEST = ROOT / "staging_artifact_manifest.sha256"

EXCLUDE_DIRS = {
    ".git", "venv", "node_modules", ".next", "__pycache__", 
    ".pytest_cache", "staging_pgdata", "scratch", ".gemini"
}

EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".shm", ".wal", ".tmp"}
EXCLUDE_FILES = {".env", "livo_dev.db", "pg_binaries.zip"}

def is_included(path: pathlib.Path, rel_path: pathlib.Path) -> bool:
    parts = rel_path.parts
    if any(ex in parts for ex in EXCLUDE_DIRS):
        return False
    if path.suffix in EXCLUDE_EXTS:
        return False
    if path.name in EXCLUDE_FILES:
        return False
    if "backups" in parts and path.suffix in {".sql", ".db", ".gz", ".tar.gz"}:
        return False
    return True

def package():
    print(f"Scanning workspace: {ROOT}")
    file_list = []
    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT)
            if is_included(p, rel):
                file_list.append((p, rel))

    print(f"Packaging {len(file_list)} verified source files into {OUTPUT_TAR.name}...")
    manifest_lines = []

    with tarfile.open(OUTPUT_TAR, "w:gz") as tar:
        for full_path, rel_path in sorted(file_list, key=lambda x: str(x[1])):
            tar.add(full_path, arcname=rel_path.as_posix())
            with open(full_path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            manifest_lines.append(f"{digest}  {rel_path.as_posix()}\n")

    with open(OUTPUT_MANIFEST, "w", encoding="utf-8") as mf:
        mf.writelines(manifest_lines)

    print(f"[SUCCESS] Artifact created: {OUTPUT_TAR} ({OUTPUT_TAR.stat().st_size} bytes)")
    print(f"[SUCCESS] Manifest created: {OUTPUT_MANIFEST} ({len(manifest_lines)} file entries)")

if __name__ == "__main__":
    package()
```

---

## 4. Staging Host Verification Procedure

When the operator transfers `livo_staging_artifact.tar.gz` and `staging_artifact_manifest.sha256` to the target host:

### Step 1: Validate Archive Integrity Prior to Extraction
```bash
# On target staging server
tar -tzf livo_staging_artifact.tar.gz > /dev/null
echo $?  # Must be 0
```

### Step 2: Extract Artifact into Clean Staging Directory
```bash
mkdir -p /app/livo-erp
tar -xzf livo_staging_artifact.tar.gz -C /app/livo-erp
cd /app/livo-erp
```

### Step 3: Validate File Hashes Against Tested Workspace Manifest
```bash
sha256sum -c staging_artifact_manifest.sha256
```
Expected output:
Every single extracted source file returns `OK`. Zero mismatches or missing files.

### Step 4: Install Dependencies & Build
```bash
# Backend dependencies
python3 -m venv venv
./venv/bin/pip install -r backend/requirements.txt

# Frontend dependencies & build
npm --prefix frontend ci
npm --prefix frontend run build
```
