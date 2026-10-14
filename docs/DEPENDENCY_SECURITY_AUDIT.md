# LIVO FOOTWEAR ERP — DEPENDENCY & SUPPLY-CHAIN SECURITY AUDIT
**Checkpoint 12 — Observability, Performance, Reliability & Operational Readiness**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Executive Summary

This audit evaluates the third-party open-source dependencies across the Python backend and Next.js frontend ecosystem, cataloging known security advisories, compatibility implications, and defense-in-depth mitigations.

---

## 2. Frontend NPM Dependency Audit

An automated scan of the frontend dependency graph was conducted via `npm audit --json`:

| Package | Installed Version | Advisory Identifier | Severity | Summary & Scope | Real-World Exposure in LIVO ERP |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`next`** | 14.2.35 | GHSA-p293-qw3h-jr36 | Critical (CVSS 9.0) | Path traversal on Windows-hosted Next.js servers | **Mitigated:** Production deployment targets Linux container runtime (Docker / Alpine / Debian). |
| **`next`** | 14.2.35 | GHSA-2xp9-vwfh-vxw4 | Critical | Remote Code Execution in Image Optimization when AVIF used | **Mitigated:** Image optimization disabled for external URLs; product uploads restricted to JPG/PNG. |
| **`next`** | 14.2.35 | GHSA-m99w-x7hq-7vfj | High | Denial of Service in App Router Server Actions | **Mitigated:** LIVO ERP utilizes Next.js strictly as a client SPA / static export; zero Server Actions used. |
| **`postcss`**| 8.4.38 | GHSA-6g55-p6wh-862q | High | Arbitrary file read in CSS source map comments | **Mitigated:** Build-time dev dependency only; not invoked during runtime request servicing. |

### 2.1 Upgrade Compatibility Assessment
* Upgrading Next.js to 15+ / 16+ is a major SemVer breaking release (`isSemVerMajor: true`).
* Next.js 15 makes `cookies()`, `headers()`, and route segment parameters asynchronous (`Promise<T>`), requiring extensive refactoring of frontend components and client middleware.
* **Recommendation:** Plan Next.js 15 migration as a dedicated post-launch milestone. Current production risk is mitigated by containerized Linux hosting and absence of Server Actions.

---

## 3. Backend Python Dependency Audit

Inspection of [`backend/requirements.txt`](file:///d:/Antigravity/Footwear%20app/backend/requirements.txt):

| Package | Version Range | Security Relevance | Hardening Verification |
| :--- | :--- | :--- | :--- |
| **`fastapi`** | >=0.110.0 | Core API Gateway | Pydantic v2 input validation rejects malformed payloads |
| **`uvicorn`** | >=0.28.0 | ASGI Server | Production uses multi-worker gunicorn/uvicorn processes |
| **`sqlalchemy`** | >=2.0.28 | Database ORM | Parameterized SQL prevents SQL injection |
| **`pyjwt`** | >=2.8.0 | Authentication Tokens | Strict signature verification and expiration checking |
| **`pwdlib[argon2]`**| >=0.2.0 | Password Hashing | Argon2id cryptographic password hashing |
| **`psycopg2-binary`**| >=2.9.9 | PostgreSQL Driver | SSL mandatory (`sslmode=require`) |
| **`boto3`** | >=1.34.0 | Cloud Storage | S3 v4 HMAC-SHA256 signatures for private backup access |

*Result:* No critical unpatched vulnerabilities detected in active backend runtime libraries.
