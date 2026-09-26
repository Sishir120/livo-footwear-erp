FROM python:3.11-slim

WORKDIR /app

# Install postgresql-client (provides pg_dump/pg_restore) and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure backup and logs directories exist
RUN mkdir -p /app/backups /app/logs

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
