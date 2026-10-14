from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_admin, COOKIE_NAME
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, UserCreate, UserUpdate
from app.core.security import verify_password, get_password_hash, create_access_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator.",
        )

    # Generate JWT token carrying user_id and company_id
    token = create_access_token(
        data={"user_id": user.id, "company_id": user.company_id, "role": user.role, "sub": user.username}
    )

    # Set httpOnly cookie as mandated by RULES.md §4
    # secure=True by default; False only when LIVO_DEV_MODE=true (local dev without HTTPS)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=86400  # 1 day
    )

    return LoginResponse(
        user=UserResponse.model_validate(user),
        message="Login successful"
    )

@router.post("/logout")
def logout(response: Response):
    # Reverse proxy hardening (Nginx, Traefik, ALB, Cloudflare):
    # Ensure cookie deletion matches exact flags (path, secure, httponly, samesite)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE
    )
    # Explicit overwrite with max_age=0 and expired date ensures immediate browser eviction
    response.set_cookie(
        key=COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE
    )
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/users", response_model=List[UserResponse])
def list_company_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists all users belonging strictly to current tenant company. Admin only."""
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_company_user(
    data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Creates a new user strictly in the admin's company.
    Client-supplied company_id or arbitrary escalation fields are prevented.
    Admin only.
    """
    existing = db.query(User).filter(User.username == data.username.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{data.username}' is already taken."
        )

    new_user = User(
        company_id=current_user.company_id,
        name=data.name.strip(),
        username=data.username.strip(),
        email=data.email.strip() if data.email else None,
        password_hash=get_password_hash(data.password),
        role=data.role,
        active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_company_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Updates user role, active status, or details strictly for current tenant company.
    Rejects cross-tenant modification (IDOR defense).
    Admin only.
    """
    target_user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your company."
        )

    if data.name is not None:
        target_user.name = data.name.strip()
    if data.email is not None:
        target_user.email = data.email.strip() if data.email else None
    if data.role is not None:
        target_user.role = data.role
    if data.active is not None:
        target_user.active = data.active

    db.commit()
    db.refresh(target_user)
    return UserResponse.model_validate(target_user)
