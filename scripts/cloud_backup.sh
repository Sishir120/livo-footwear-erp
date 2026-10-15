#!/usr/bin/env bash
# ==============================================================================
# LIVO FOOTWEAR ERP — CLOUD DATABASE BACKUP & ROTATION ENGINE
# ==============================================================================
# Usage:
#   TARGET_DATABASE_URL="postgresql://user:pass@host:5432/dbname?sslmode=require" ./scripts/cloud_backup.sh
# Safeguards:
#   1. Idempotency & Overlap Prevention: Uses flock lockfile to block concurrent executions.
#   2. Zero Credential Leakage: Database URL is redacted from logs, status files, and error traces.
#   3. Integrity Verification: Computes and logs SHA-256 checksum for every backup artifact.
#   4. Retention Pruning: Automatically deletes expired backup archives.
#   5. Structured Telemetry: Records JSON status artifact for health probe consumption.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
STATUS_FILE="${BACKUP_DIR}/latest_status.json"
LOCK_FILE="/tmp/livo_backup.lock"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

# 1. Overlap Protection via Lockfile
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [ERROR] Another backup process is currently running. Exiting to prevent overlap." >&2
    exit 1
fi

# 2. Database Target Resolution
DB_URL="${TARGET_DATABASE_URL:-${DATABASE_URL:-}}"
if [ -z "${DB_URL}" ]; then
    echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [ERROR] Neither TARGET_DATABASE_URL nor DATABASE_URL is configured." >&2
    exit 1
fi

TIMESTAMP="$(date -u +"%Y%m%d_%H%M%SZ")"
BACKUP_FILENAME="livo_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [INFO] Initiating database dump for target database..."

# 3. Native pg_dump Execution
START_TIME=$(date +%s)

if ! pg_dump "${DB_URL}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    --quote-all-identifiers \
    | gzip > "${BACKUP_PATH}"; then
    
    echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [CRITICAL] pg_dump failed!" >&2
    
    # Emit failure telemetry without credentials
    cat <<EOF > "${STATUS_FILE}"
{
  "status": "failed",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "error": "pg_dump command execution failed",
  "file_name": "${BACKUP_FILENAME}"
}
EOF

    # Optional webhook alerting
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -s -X POST -H "Content-Type: application/json" \
            -d "{\"text\":\"[ALERT] LIVO ERP Automated Backup FAILED at $(date -u +"%Y-%m-%d %H:%M:%SZ")\"}" \
            "${ALERT_WEBHOOK_URL}" || true
    fi
    exit 2
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 4. Measure Size and Checksum
FILE_SIZE=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null || stat -f%z "${BACKUP_PATH}" 2>/dev/null || wc -c < "${BACKUP_PATH}")
SHA256=$(sha256sum "${BACKUP_PATH}" 2>/dev/null | awk '{print $1}' || shasum -a 256 "${BACKUP_PATH}" 2>/dev/null | awk '{print $1}' || echo "checksum_unavailable")

echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [SUCCESS] Backup completed in ${DURATION}s."
echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [ARTIFACT] Size: ${FILE_SIZE} bytes | SHA256: ${SHA256}"

# 5. Record Structured JSON Telemetry
cat <<EOF > "${STATUS_FILE}"
{
  "status": "success",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "file_name": "${BACKUP_FILENAME}",
  "file_size_bytes": ${FILE_SIZE},
  "sha256": "${SHA256}",
  "duration_seconds": ${DURATION},
  "retention_days": ${RETENTION_DAYS},
  "storage_destination": "local"
}
EOF

# 6. Retention Pruning (Delete local backups older than retention threshold)
find "${BACKUP_DIR}" -name "livo_backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
echo "[$(date -u +"%Y-%m-%d %H:%M:%SZ")] [INFO] Pruned local backups older than ${RETENTION_DAYS} days."
