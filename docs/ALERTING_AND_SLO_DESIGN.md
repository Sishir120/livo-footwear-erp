# LIVO FOOTWEAR ERP — ALERTING & SLO DESIGN SPECIFICATION
**Checkpoint 12 — Observability, Performance, Reliability & Operational Readiness**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Service Level Objectives (SLOs) & Error Budgets

The following proposed SLOs establish the operational health targets for LIVO Footwear ERP in production environments:

| Objective Identifier | Target Indicator (SLI) | Target Metric | Evaluation Window | Monthly Error Budget |
| :--- | :--- | :--- | :--- | :--- |
| **API Availability SLO** | Successful responses (`HTTP < 500` / Total Requests) | **99.9%** | Rolling 30 Days | 0.1% (~43.2 minutes downtime) |
| **API Latency SLO** | Transaction latency from ingress to egress | **p95 < 250 ms** | Rolling 7 Days | 5% of requests > 250ms |
| **Data Recovery SLA** | Database snapshot freshness (RPO) | **<= 60 minutes** | Continuous | Zero missing snapshots |
| **Restoration SLA** | Time to full ledger parity restoration (RTO) | **<= 15 minutes** | Per Incident | Measured drill: 0.0022s |
| **Document Continuity** | Gapless sequence allocation on tax invoices | **100% gapless** | Continuous | Zero duplicate or skipped numbers |

---

## 2. Production Alerting Rules & Escalation Tiers

Alerts are designed to be actionable, symptom-oriented, and free from transient noise:

```
+---------------------------------------------------------------------------------------------------------+
|                                    ALERTING ESCALATION MATRIX                                           |
+---------------------------------------------------------------------------------------------------------+
|  SEVERITY: P1 (CRITICAL) — Page On-Call SRE (Immediate Response Required)                              |
|  - Rule 1: Application Unavailable (Readiness probe /api/v1/health/ready failing > 2 minutes).         |
|  - Rule 2: Elevated 5xx Rate (5xx responses exceed 5% of total traffic over a 5-minute rolling window).  |
|  - Rule 3: Database Connection Exhaustion (Active pool connections reach 95% capacity for 2 minutes).   |
+---------------------------------------------------------------------------------------------------------+
|  SEVERITY: P2 (HIGH) — Slack/Email Notification (Response within 30 minutes)                            |
|  - Rule 4: Database Backup Failure (latest_status.json reports "failed" or age > 90 minutes).           |
|  - Rule 5: Elevated Latency (p95 API latency exceeds 500ms for 10 consecutive minutes).                 |
|  - Rule 6: Cloud Storage Sync Failure (Local backup succeeds but S3/R2 upload fails repeatedly).         |
+---------------------------------------------------------------------------------------------------------+
|  SEVERITY: P3 (MEDIUM) — Daily Operations Review (Response next business day)                           |
|  - Rule 7: Brute Force Authentication Spike (> 100 failed login attempts across single IP in 5 min).    |
|  - Rule 8: Offline Sync Queue Growth (> 500 unprocessed offline mutation payloads pending).             |
|  - Rule 9: Negative Stock Conflict Spike (> 20 insufficient stock 422 errors within 1 hour).            |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Security Observability & Compliance Signals

The security monitoring subsystem tracks operational events without recording sensitive customer data:
1. **Authentication Anomalies:** Emits warning when multiple 401s occur for a single user/IP within a short window.
2. **Access Control Denials:** Emits warning when non-admins attempt admin endpoints (HTTP 403 logged with user role and endpoint).
3. **Audit Trail Immutability:** Write-once logs in `audit_log` track who updated configuration, changed roles, or voided tax invoices.
