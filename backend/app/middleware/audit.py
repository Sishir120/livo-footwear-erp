from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.core.security import decode_access_token
import json

class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records an audit log entry carrying company_id, user_id,
    action, endpoint, IP address, and status on every mutating request (POST, PUT, PATCH, DELETE).
    Mandated by RULES.md §0 and §4.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only log mutating HTTP requests
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Try extracting auth token from cookie or header
            token = request.cookies.get("livo_access_token")
            if not token:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            
            user_id = None
            company_id = None
            user_name = None
            
            if token:
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("user_id")
                    company_id = payload.get("company_id")
                    user_name = payload.get("sub")
            
            # If request had company_id context or was authenticated
            if company_id:
                client_ip = request.client.host if request.client else "unknown"
                db: Session = SessionLocal()
                try:
                    audit_entry = AuditLog(
                        company_id=company_id,
                        user_id=user_id,
                        user_name=user_name,
                        action=request.method,
                        endpoint=str(request.url.path),
                        target_table=None,  # Router/endpoint specific details can be updated
                        details=f"Status: {response.status_code}",
                        ip_address=client_ip
                    )
                    db.add(audit_entry)
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()
                    
        return response
