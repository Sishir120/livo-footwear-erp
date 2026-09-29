from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, COOKIE_NAME
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.core.security import verify_password, create_access_token
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
