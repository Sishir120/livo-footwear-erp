from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

COOKIE_NAME = "livo_access_token"

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # Fallback check for Bearer header for API testing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Session cookie missing.",
        )
        
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )
        
    user_id = payload.get("user_id")
    company_id = payload.get("company_id")
    if not user_id or not company_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid.",
        )
        
    user = db.query(User).filter(User.id == user_id, User.company_id == company_id, User.active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    # Set company_id in contextvar for structured logging
    from app.middleware.correlation import set_company_id
    set_company_id(user.company_id)
        
    return user

def require_editor(current_user: User = Depends(get_current_user)) -> User:
    """
    Enforces 'editor' role requirement for mutating operations.
    Rejects viewers at the API layer as mandated by RULES.md §0 and §4.
    """
    if current_user.role != "editor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Role 'editor' is required for modifying data.",
        )
    return current_user
