
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.security import create_token_pair, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["Authentication"])


@router.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a user with a unique username/email and a hashed password."""
    email = str(payload.email).lower()
    existing = db.scalar(
        select(User).where(or_(User.email == email, User.username == payload.username))
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already registered")

    user = User(
        username=payload.username.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@router.post("/token/", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate using email and password, then return JWT token pair."""
    email = str(payload.email).lower()
    password = payload.password

    user = db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    return create_token_pair(str(user.id))


@router.post("/token/refresh/", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access/refresh pair."""
    try:
        claims = jwt.decode(
            payload.refresh,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if claims.get("type") != "refresh":
            raise ValueError("Wrong token type")
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return create_token_pair(str(user.id))
