"""
LIVO Footwear ERP — Staging PostgreSQL Cluster Controller
Manages an isolated PostgreSQL 18 instance with persistent storage,
creates staging databases, and provisions staging users.
"""

import os
import sys
import pathlib
import psycopg2
from embedded_postgres import PostgresServer

STAGING_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "staging_pgdata"

def get_or_start_staging_server():
    """Initializes and starts the isolated PostgreSQL 18 staging cluster."""
    STAGING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = PostgresServer(STAGING_DATA_DIR, cleanup_mode=None)
    server.ensure_pgdata_inited()
    server.ensure_postgres_running()
    return server

def provision_staging_database():
    server = get_or_start_staging_server()
    master_uri = server.get_uri("postgres")
    
    conn = psycopg2.connect(master_uri)
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. Create livo_staging_user if not exists
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'livo_staging_user'")
    if not cur.fetchone():
        cur.execute("CREATE USER livo_staging_user WITH PASSWORD 'LivoStaging2026!'")
        print("Created role: livo_staging_user")
    else:
        print("Role livo_staging_user already exists.")
        
    # 2. Create livo_staging database if not exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'livo_staging'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE livo_staging OWNER livo_staging_user")
        print("Created database: livo_staging (owned by livo_staging_user)")
    else:
        print("Database livo_staging already exists.")
        
    cur.close()
    conn.close()
    
    # Return connection details
    staging_uri = server.get_uri("livo_staging")
    # Replace default user with livo_staging_user if needed, or use postgres
    print("\n" + "=" * 60)
    print("STAGING POSTGRESQL 18 CLUSTER IS OPERATIONAL")
    print(f"Master URI:   {master_uri}")
    print(f"Staging URI:  {staging_uri}")
    print(f"Data Dir:     {STAGING_DATA_DIR}")
    print("=" * 60)
    return staging_uri

if __name__ == "__main__":
    uri = provision_staging_database()
