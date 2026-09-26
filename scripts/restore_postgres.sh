#!/usr/bin/env bash
set -euo pipefail

# LIVO GROUP Footwear ERP — PostgreSQL Database Restore Script
# Usage: ./scripts/restore_postgres.sh <path_to_backup.sql.gz> [target_db_name]

if [ $# -lt 1 ]; then
    echo "Error: Backup file path required."
    echo "Usage: $0 <path_to_backup.sql.gz> [target_db_name]"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-${POSTGRES_DB:-livo_erp}}"
DB_USER="${POSTGRES_USER:-livo_admin}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' not found."
    exit 1
fi

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Restoring database '${TARGET_DB}' from '${BACKUP_FILE}'..."

# Decompress and feed into target postgres database container
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | docker compose exec -T postgres psql -U "${DB_USER}" -d "${TARGET_DB}"
else
    cat "${BACKUP_FILE}" | docker compose exec -T postgres psql -U "${DB_USER}" -d "${TARGET_DB}"
fi

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Restore completed successfully into '${TARGET_DB}'."
