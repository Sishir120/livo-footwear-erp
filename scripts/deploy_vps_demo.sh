#!/usr/bin/env bash
# ==============================================================================
# LIVO FOOTWEAR ERP — AUTOMATED STAGING / DEMO VPS PROVISIONING & DEPLOYMENT SCRIPT
# ==============================================================================
# Target OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
# Target Stack:
#   - Database: PostgreSQL 16
#   - Backend:  Python 3.11 + FastAPI + Uvicorn (port 8000)
#   - Frontend: Node.js 20 LTS + Next.js 14 (port 3000)
#   - Edge/TLS: Caddy 2 Reverse Proxy with Auto-HTTPS
#
# Usage:
#   sudo ./scripts/deploy_vps_demo.sh [options]
#
# Environment / Option Overrides:
#   DOMAIN="demo.livogroup.com"          Domain name for Caddy automatic TLS
#   APP_DIR="/opt/livo-erp"              Target installation directory
#   DB_NAME="livo_erp"                   PostgreSQL database name
#   DB_USER="livo_user"                  PostgreSQL database role
#   DB_PASSWORD="<generated-or-custom>"  PostgreSQL password
#   LIVO_BRANCH="release/v1.0.0-demo-candidate" Git branch to clone or verify
# ==============================================================================

set -euo pipefail
IFS=$'\n\t'

# ------------------------------------------------------------------------------
# 0. CONFIGURATION & COLOR CONSTANTS
# ------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_header()  {
    echo -e "\n${PURPLE}==============================================================================${NC}"
    echo -e "${CYAN} $1 ${NC}"
    echo -e "${PURPLE}==============================================================================${NC}"
}

# Ensure root privileges
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be executed as root (e.g. via sudo)."
    exit 1
fi

DOMAIN="${DOMAIN:-demo.livogroup.com}"
APP_DIR="${APP_DIR:-/opt/livo-erp}"
DB_NAME="${DB_NAME:-livo_erp}"
DB_USER="${DB_USER:-livo_user}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 16)}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
LIVO_BRANCH="${LIVO_BRANCH:-release/v1.0.0-demo-candidate}"
REPO_URL="${REPO_URL:-https://github.com/Sishir120/livo-footwear-erp.git}"
BACKEND_PORT=8000
FRONTEND_PORT=3000

log_header "LIVO FOOTWEAR ERP — VPS DEPLOYMENT INITIALIZING"
log_info "Target Domain:           ${DOMAIN}"
log_info "Deployment Root:         ${APP_DIR}"
log_info "Database:                ${DB_NAME} (User: ${DB_USER})"
log_info "Release Branch:          ${LIVO_BRANCH}"

# ------------------------------------------------------------------------------
# 1. BASE OS REPOSITORIES & DEPENDENCIES
# ------------------------------------------------------------------------------
log_header "STEP 1: REPOSITORIES & RUNTIME DEPENDENCIES"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    git \
    build-essential \
    libpq-dev \
    ufw \
    openssl \
    tar \
    software-properties-common

# 1.1 Python 3.11 Runtime Installation
log_info "Configuring Python 3.11 environment..."
UBUNTU_CODENAME="$(lsb_release -cs)"
if ! command -v python3.11 &>/dev/null; then
    if [[ "${UBUNTU_CODENAME}" == "jammy" ]]; then
        log_info "Ubuntu 22.04 detected: Adding deadsnakes PPA for Python 3.11..."
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update -y
    fi
    apt-get install -y python3.11 python3.11-venv python3.11-dev
fi
PYTHON_BIN="$(command -v python3.11 || command -v python3)"
log_success "Using Python: $($PYTHON_BIN --version)"

# 1.2 Node.js 20 LTS Repository & Runtime
log_info "Configuring Node.js 20 LTS runtime..."
if ! command -v node &>/dev/null || [[ "$(node -v | cut -d'.' -f1)" != "v20" ]]; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg --yes
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
    apt-get update -y
    apt-get install -y nodejs
fi
log_success "Using Node.js: $(node --version) / npm: $(npm --version)"

# 1.3 PostgreSQL 16 Official PGDG Repository
log_info "Configuring PostgreSQL 16 official PGDG repository..."
if ! command -v psql &>/dev/null; then
    install -d /etc/apt/keyrings
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg --yes
    echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt ${UBUNTU_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    apt-get update -y
    apt-get install -y postgresql-16 postgresql-client-16
fi
systemctl enable postgresql
systemctl start postgresql
log_success "PostgreSQL active: $(psql --version)"

# 1.4 Caddy Web Server (Reverse Proxy with Automatic SSL/TLS)
log_info "Configuring Caddy web server repository..."
if ! command -v caddy &>/dev/null; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg --yes
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -y
    apt-get install -y caddy
fi
systemctl enable caddy
log_success "Caddy installed: $(caddy version)"

# ------------------------------------------------------------------------------
# 2. POSTGRESQL DATABASE & USER PROVISIONING
# ------------------------------------------------------------------------------
log_header "STEP 2: POSTGRESQL 16 PROVISIONING"

log_info "Ensuring PostgreSQL role '${DB_USER}' and database '${DB_NAME}' exist..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}' CREATEDB;"

sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER} ENCODING 'UTF8' LC_COLLATE 'C.UTF-8' LC_CTYPE 'C.UTF-8';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
log_success "Database '${DB_NAME}' configured and permissions verified."

DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}"

# ------------------------------------------------------------------------------
# 3. APPLICATION CODEBASE SETUP & REPOSITORIES
# ------------------------------------------------------------------------------
log_header "STEP 3: APPLICATION REPOSITORY PREPARATION"

CURRENT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${CURRENT_SCRIPT_DIR}/.." && pwd)"

if [[ -f "${WORKSPACE_ROOT}/backend/alembic.ini" && -d "${WORKSPACE_ROOT}/frontend/src" ]]; then
    log_info "Detected existing checkout at ${WORKSPACE_ROOT}. Synchronizing into ${APP_DIR}..."
    mkdir -p "${APP_DIR}"
    if [[ "${WORKSPACE_ROOT}" != "${APP_DIR}" ]]; then
        rsync -a --exclude='.git' --exclude='node_modules' --exclude='venv' --exclude='livo_dev.db' "${WORKSPACE_ROOT}/" "${APP_DIR}/"
    fi
else
    log_info "Cloning branch ${LIVO_BRANCH} from ${REPO_URL} into ${APP_DIR}..."
    if [[ ! -d "${APP_DIR}/.git" ]]; then
        git clone --branch "${LIVO_BRANCH}" --depth 1 "${REPO_URL}" "${APP_DIR}"
    else
        cd "${APP_DIR}"
        git fetch origin "${LIVO_BRANCH}"
        git checkout "${LIVO_BRANCH}"
        git pull origin "${LIVO_BRANCH}"
    fi
fi

# Ensure dedicated system service user 'livo' exists
if ! id -u livo &>/dev/null; then
    log_info "Creating non-privileged system user 'livo'..."
    useradd -r -s /bin/bash -d "${APP_DIR}" livo
fi
chown -R livo:livo "${APP_DIR}"

# ------------------------------------------------------------------------------
# 4. BACKEND ENVIRONMENT, VENV & ALEMBIC MIGRATIONS
# ------------------------------------------------------------------------------
log_header "STEP 4: BACKEND PROVISIONING & MIGRATIONS"

BACKEND_DIR="${APP_DIR}/backend"
cd "${BACKEND_DIR}"

# Create Virtual Environment
if [[ ! -d "${BACKEND_DIR}/venv" ]]; then
    log_info "Creating Python 3.11 virtual environment..."
    sudo -u livo "${PYTHON_BIN}" -m venv "${BACKEND_DIR}/venv"
fi

sudo -u livo "${BACKEND_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel
sudo -u livo "${BACKEND_DIR}/venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

# Generate backend .env configuration
BACKEND_ENV_FILE="${BACKEND_DIR}/.env"
log_info "Generating production configuration at ${BACKEND_ENV_FILE}..."
cat <<EOF > "${BACKEND_ENV_FILE}"
# Production Configuration for LIVO Footwear ERP
ENVIRONMENT=production
LIVO_DEV_MODE=false
PROJECT_NAME="LIVO FOOTWEAR ERP (STAGING/DEMO)"
VERSION=1.0.0

SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

DATABASE_URL=${DATABASE_URL}
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=15
DB_POOL_RECYCLE=1800

BACKEND_CORS_ORIGINS=https://${DOMAIN},http://localhost:3000,http://127.0.0.1:3000
COOKIE_SAMESITE=lax
TRUSTED_PROXIES=127.0.0.1,::1
EOF
chown livo:livo "${BACKEND_ENV_FILE}"
chmod 600 "${BACKEND_ENV_FILE}"

# Execute Alembic Migrations
log_info "Executing Alembic schema migrations up to head (including 020_fixed_assets_waste_and_expenses)..."
sudo -u livo "${BACKEND_DIR}/venv/bin/alembic" upgrade head

CURRENT_REVISION=$(sudo -u livo "${BACKEND_DIR}/venv/bin/alembic" current 2>&1 | tr -d '\r')
log_success "Alembic schema current state: ${CURRENT_REVISION}"

# Seed Realistic Footwear Demo Data
log_info "Executing realistic footwear demo seeder (Paris Points 32-43, BS 2083 dates, advances)..."
sudo -u livo "${BACKEND_DIR}/venv/bin/python" "${BACKEND_DIR}/scripts/seed_footwear_demo.py" --db-url "${DATABASE_URL}"

# ------------------------------------------------------------------------------
# 5. FRONTEND ENVIRONMENT & PRODUCTION BUILD
# ------------------------------------------------------------------------------
log_header "STEP 5: FRONTEND PRODUCTION BUILD"

FRONTEND_DIR="${APP_DIR}/frontend"
cd "${FRONTEND_DIR}"

FRONTEND_ENV_FILE="${FRONTEND_DIR}/.env.production"
cat <<EOF > "${FRONTEND_ENV_FILE}"
NEXT_PUBLIC_API_URL=https://${DOMAIN}
NODE_ENV=production
EOF
chown livo:livo "${FRONTEND_ENV_FILE}"

log_info "Installing npm dependencies..."
sudo -u livo npm --prefix "${FRONTEND_DIR}" ci || sudo -u livo npm --prefix "${FRONTEND_DIR}" install

log_info "Compiling Next.js production build..."
sudo -u livo npm --prefix "${FRONTEND_DIR}" run build
log_success "Next.js build succeeded."

# ------------------------------------------------------------------------------
# 6. SYSTEMD SERVICE DAEMONS SETUP
# ------------------------------------------------------------------------------
log_header "STEP 6: SYSTEMD SERVICES (UVICORN & NEXT.JS)"

# 6.1 Backend Service: Uvicorn on 127.0.0.1:8000
cat <<EOF > /etc/systemd/system/livo-backend.service
[Unit]
Description=LIVO Footwear ERP - FastAPI Backend Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=livo
Group=livo
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${BACKEND_ENV_FILE}
ExecStart=${BACKEND_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT} --workers 2 --proxy-headers --forwarded-allow-ips='*'
Restart=always
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# 6.2 Frontend Service: Next.js on 127.0.0.1:3000
cat <<EOF > /etc/systemd/system/livo-frontend.service
[Unit]
Description=LIVO Footwear ERP - Next.js Frontend Service
After=network.target livo-backend.service

[Service]
Type=simple
User=livo
Group=livo
WorkingDirectory=${FRONTEND_DIR}
Environment=NODE_ENV=production
Environment=PORT=${FRONTEND_PORT}
ExecStart=/usr/bin/npm start -- -p ${FRONTEND_PORT}
Restart=always
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable livo-backend
systemctl restart livo-backend
systemctl enable livo-frontend
systemctl restart livo-frontend

log_success "Systemd services livo-backend and livo-frontend enabled and started."

# ------------------------------------------------------------------------------
# 7. CADDY REVERSE PROXY & AUTOMATIC TLS
# ------------------------------------------------------------------------------
log_header "STEP 7: CADDY REVERSE PROXY & TLS TERMINATION"

CADDY_CONFIG="/etc/caddy/Caddyfile"
log_info "Configuring ${CADDY_CONFIG} for ${DOMAIN}..."

cat <<EOF > "${CADDY_CONFIG}"
${DOMAIN} {
    # Reverse proxy API and OpenAPI endpoints directly to FastAPI backend
    handle /api/* {
        reverse_proxy 127.0.0.1:${BACKEND_PORT}
    }
    handle /health/* {
        reverse_proxy 127.0.0.1:${BACKEND_PORT}
    }
    handle /docs* {
        reverse_proxy 127.0.0.1:${BACKEND_PORT}
    }
    handle /openapi.json {
        reverse_proxy 127.0.0.1:${BACKEND_PORT}
    }

    # Reverse proxy all web frontend pages to Next.js
    handle {
        reverse_proxy 127.0.0.1:${FRONTEND_PORT}
    }

    # Security & HSTS headers per ARCHITECTURE.md
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Structured logging
    log {
        output file /var/log/caddy/livo_access.log {
            roll_size 50mb
            roll_keep 5
        }
    }
}
EOF

mkdir -p /var/log/caddy
chown -R caddy:caddy /var/log/caddy
systemctl reload caddy || systemctl restart caddy
log_success "Caddy configuration active with automatic SSL/TLS termination."

# Configure Firewall (UFW)
if ufw status | grep -q "Status: active"; then
    log_info "Configuring UFW firewall rules for HTTP, HTTPS, and SSH..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw reload
fi

# ------------------------------------------------------------------------------
# 8. POST-DEPLOYMENT SMOKE TEST & VERIFICATION
# ------------------------------------------------------------------------------
log_header "STEP 8: SMOKE TEST VERIFICATION"

sleep 3

log_info "Testing Backend direct health check (127.0.0.1:${BACKEND_PORT}/health)..."
BACKEND_HEALTH_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BACKEND_PORT}/health" || echo "FAILED")
if [[ "${BACKEND_HEALTH_HTTP}" == "200" ]]; then
    log_success "Backend /health returned HTTP 200 OK"
else
    log_warn "Backend /health returned HTTP ${BACKEND_HEALTH_HTTP}"
fi

log_info "Testing Frontend /login page (127.0.0.1:${FRONTEND_PORT}/login)..."
FRONTEND_LOGIN_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_PORT}/login" || echo "FAILED")
if [[ "${FRONTEND_LOGIN_HTTP}" == "200" ]]; then
    log_success "Frontend /login returned HTTP 200 OK (no redirect loops)"
else
    log_warn "Frontend /login returned HTTP ${FRONTEND_LOGIN_HTTP}"
fi

# ------------------------------------------------------------------------------
# 9. EXECUTIVE DEPLOYMENT SUMMARY
# ------------------------------------------------------------------------------
log_header "DEPLOYMENT COMPLETED SUCCESSFULLY"
cat <<EOF

LIVO FOOTWEAR ERP — CLIENT DEMO ENVIRONMENT IS READY!
==============================================================================
Live Demo URL:         https://${DOMAIN}
Backend Health Probe:  https://${DOMAIN}/health
Direct API Docs:       https://${DOMAIN}/docs

Database Credentials:
  - Database:          ${DB_NAME}
  - Role:              ${DB_USER}
  - Password:          ${DB_PASSWORD}
  - Connection:        ${DATABASE_URL}

Client Demo Personas:
  1. System Administrator:
     Username:         admin_demo
     Password:         LivoAdmin2026!
     Permissions:      Full Administrative Access & Master Override

  2. Compliance Auditor / Viewer:
     Username:         viewer_demo
     Password:         LivoViewer2026!
     Permissions:      Read-Only Financial, Audit & Stock Verification

Management Commands:
  - Backend Status:    systemctl status livo-backend
  - Frontend Status:   systemctl status livo-frontend
  - Caddy Status:      systemctl status caddy
  - Backend Logs:      journalctl -u livo-backend -f
  - Frontend Logs:     journalctl -u livo-frontend -f
  - Alembic Status:    cd ${BACKEND_DIR} && ./venv/bin/alembic current
==============================================================================
EOF
