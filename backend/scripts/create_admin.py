"""
LIVO Footwear ERP — Initial Administrator Account Provisioning CLI
Usage:
  python scripts/create_admin.py --username admin --email admin@example.com
Or interactive:
  python scripts/create_admin.py
"""

import sys
import os
import argparse
import getpass
import pathlib

backend_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.core.security import get_password_hash

def create_admin(username: str, email: str, password: str, name: str = "System Administrator"):
    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    with SessionLocal() as db:
        company = db.query(Company).filter(Company.code == "LIVO").first()
        if not company:
            print("[ERROR] Default tenant company 'LIVO' not found. Run database migrations first.")
            sys.exit(1)

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"[ERROR] User with username '{username}' already exists.")
            sys.exit(1)

        user = User(
            company_id=company.id,
            name=name,
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            role="admin",
            active=True
        )
        db.add(user)
        db.commit()
        print(f"[SUCCESS] Administrator account '{username}' ({email}) created successfully for company '{company.name}'.")

def main():
    parser = argparse.ArgumentParser(description="Create initial administrator user for LIVO ERP")
    parser.add_argument("--username", help="Administrator username", default=os.getenv("LIVO_ADMIN_USERNAME"))
    parser.add_argument("--email", help="Administrator email", default=os.getenv("LIVO_ADMIN_EMAIL"))
    parser.add_argument("--name", help="Administrator full name", default=os.getenv("LIVO_ADMIN_NAME", "System Administrator"))
    parser.add_argument("--password", help="Administrator password (insecure if passed on command line)", default=os.getenv("LIVO_ADMIN_PASSWORD"))

    args = parser.parse_args()

    username = args.username or input("Enter administrator username: ").strip()
    email = args.email or input("Enter administrator email: ").strip()
    name = args.name or input("Enter full name: ").strip()
    password = args.password or getpass.getpass("Enter administrator password: ")

    if not username or not email or not password:
        print("[ERROR] Username, email, and password are required.")
        sys.exit(1)

    create_admin(username, email, password, name)

if __name__ == "__main__":
    main()
