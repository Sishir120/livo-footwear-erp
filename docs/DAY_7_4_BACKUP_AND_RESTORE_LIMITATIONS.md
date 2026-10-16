# LIVO Footwear ERP — Day 7.4 Backup & Restore Limitations Report

**Phase:** Day 7.4 Final Artifact Identity & Staging Authorization Gate  
**Timestamp:** 2026-10-16T15:58:00+05:45  
**Workspace:** `D:\Antigravity\Footwear app`  
**Test Suite:** `backend/tests/test_day_7_4_remote_backup_and_quiescence.py` (6 Passed)  

---

## 1. Remote S3/B2 Replication Implementation Status

A comprehensive source inspection of `backend/app/services/backup_service.py` was conducted to verify remote backup claims without deploying cloud resources.

### Implementation Status: **IMPLEMENTED BUT DISABLED PENDING CONFIGURATION** (Partial Scope)

The codebase implements a single one-way cloud upload function:
```python
def upload_to_cloud_storage(file_path: Path, destination_key: str) -> Optional[str]:
    if not (settings.STORAGE_ENDPOINT_URL and settings.STORAGE_ACCESS_KEY and settings.STORAGE_SECRET_KEY):
        return None  # Cloud storage not configured; local backup retained
    ...
    s3 = boto3.client("s3", endpoint_url=settings.STORAGE_ENDPOINT_URL, ...)
    s3.upload_file(Filename=str(file_path), Bucket=settings.STORAGE_BUCKET_NAME, Key=destination_key)
    return f"s3://{settings.STORAGE_BUCKET_NAME}/{destination_key}"
```

### Critical Gaps in Remote Backup Architecture
1. **Omission of Physical File Uploads:**  
   `run_storage_backup()` (which archives worker citizenship scans, profile photos, and product images) **never calls `upload_to_cloud_storage`**. All physical files remain strictly on the local host.
2. **Omission of Manifest Metadata:**  
   The audit manifest (`livo_manifest_*.json`), which links database dumps to physical file hashes and system states, is **never uploaded to remote storage**.
3. **Absence of Remote Restoration Interface:**  
   There is **no** `download_from_cloud_storage` or `restore_from_cloud_storage` function in `backup_service.py`. The restore engine only operates on local file paths (`restore_database_backup(backup_file_path)`). In an outage, operators must manually download dumps using AWS CLI or Backblaze B2 web console.
4. **Absence of Cloud Lifecycle/Retention Management:**  
   The application does not enforce lifecycle rules or retention deletion on remote S3 buckets. Indefinite uploads will incur unmanaged cloud storage costs unless bucket lifecycle policies are manually configured in cloud provider consoles.

---

## 2. Automated Forensic Verification (Mocked Unit Tests)

Forensic tests in `backend/tests/test_day_7_4_remote_backup_and_quiescence.py` verified the following behaviors without contacting external networks:

| Test Case | Scenario | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- |
| `test_cloud_upload_disabled_when_unconfigured` | Empty S3 environment variables | Returns `None`, retains local file | **PASSED** |
| `test_cloud_upload_success_with_mock_s3` | Valid credentials with mock `boto3` | Calls `upload_file`, returns S3 URI | **PASSED** |
| `test_cloud_upload_failure_retains_local_and_warns` | S3 network timeout (504 Gateway Timeout) | Catches error, records warning in status data, retains local `.db`/`.sql` file | **PASSED** |
| `test_storage_backup_does_not_upload_to_cloud` | Execute file storage archive | Confirms `upload_to_cloud_storage` is never invoked | **PASSED** |
| `test_absence_of_remote_restore_function` | Inspect `backup_service` API surface | Confirms no automated cloud download/restore method exists | **PASSED** |
| `test_restore_fails_safely_on_corrupted_file` | Restore from non-existent/corrupted file | Fails closed with `FileNotFoundError`/`ValueError` | **PASSED** |

**Operational Statement:**  
Because remote restoration has never been exercised against a live S3/B2 endpoint, **remote backup protection CANNOT be classified as operationally verified**.

---

## 3. Backup Quiescence, Concurrency, and Recovery Invariants

### 3.1 Write Quiescence Reality
- **Software Enforcement:** The application contains **no software-enforced write-lock or transaction pause mechanism** during backup execution. Application writes are neither blocked nor detected by `run_database_backup`.
- **Database Consistency (PostgreSQL):** `pg_dump` utilizes PostgreSQL MVCC snapshot isolation (`SERIALIZABLE` or `REPEATABLE READ` snapshot). The resulting database dump is internally consistent as of the exact instant `pg_dump` began.
- **Cross-Artifact Consistency Gap:** MVCC snapshot isolation protects only PostgreSQL data. It does **not** protect physical files in `backend/storage/` or `static/uploads/`.
- **Operator Requirement:** A **2-minute reverse-proxy maintenance window** (serving HTTP 503 via Caddy/Nginx) is mandatory to guarantee that no user uploads or writes occur between the database dump and the physical file tarball.

### 3.2 Recovery Failure Modes & Residual Risks
1. **Crash Between DB Dump and File Tarball:**  
   If a crash occurs after the database dump completes but before `run_storage_backup` finishes, the resulting backup pair will have mismatched timestamps. Recovery would restore a newer database with missing uploaded files referenced in `ProductImage` or `Worker`.
2. **Stale/Mismatched Manifest:**  
   If an operator attempts restoration using mismatched database dumps and file archives, foreign key constraints will succeed, but media URLs in the frontend will return 404.
3. **Partial Restore Failure:**  
   If `psql` restore aborts halfway through (e.g. out of memory or syntax mismatch), the database is left in a partially loaded state. The restore procedure does **not** automatically rollback prior tables. Operators must explicitly execute `DROP DATABASE` and `CREATE DATABASE` before re-attempting restore.
