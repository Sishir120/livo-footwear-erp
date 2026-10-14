FROM python:3.11-slim

WORKDIR /app

# Install postgresql-client (provides pg_dump/pg_restore) and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r livo && useradd -r -g livo -d /app -s /sbin/nologin livo

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure backup, logs, storage, and upload directories exist with non-root ownership
RUN mkdir -p /app/backups /app/logs /app/static/uploads/products /app/storage/secure_hr \
    && chown -R livo:livo /app

USER livo

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
