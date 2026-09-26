#!/usr/bin/env bash
set -euo pipefail

# LIVO GROUP Footwear ERP — Nightly PostgreSQL Backup
# Usage: ./scripts/backup_nightly.sh

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP="$(date -u +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/livo_dump_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Starting PostgreSQL nightly backup..."

# 1. Run real pg_dump from the Postgres container
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-livo_admin}" "${POSTGRES_DB:-livo_erp}" | gzip > "${BACKUP_FILE}"

FILESIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || wc -c < "${BACKUP_FILE}")
echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] pg_dump completed: ${BACKUP_FILE} (${FILESIZE} bytes)"

# 2. Upload to Cloud Storage via rclone (Backblaze B2 / Cloudflare R2 per ARCHITECTURE.md §9)
if command -v rclone &> /dev/null; then
    if rclone listremotes | grep -q "livo_r2:"; then
        echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Uploading to Cloudflare R2 via rclone..."
        rclone copy "${BACKUP_FILE}" "livo_r2:livo-erp-storage/backups/"
        echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Cloud upload successful."
    elif rclone listremotes | grep -q "livo_b2:"; then
        echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Uploading to Backblaze B2 via rclone..."
        rclone copy "${BACKUP_FILE}" "livo_b2:livo-erp-storage/backups/"
        echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Cloud upload successful."
    else
        echo "[WARNING] rclone remote 'livo_r2:' or 'livo_b2:' not found in rclone config. Retaining local backup only."
    fi
else
    echo "[INFO] rclone binary not installed on host. Retaining local backup."
fi

# 3. Retention policy: delete local backups older than 30 days
find "${BACKUP_DIR}" -name "livo_dump_*.sql.gz" -type f -mtime +30 -delete

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Nightly backup procedure finished."
