from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a one-way password hash suitable for database storage."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a submitted password against its stored hash."""
    return password_hash.verify(password, hashed_password)


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Create a signed JWT with an explicit token type and expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(subject: str) -> dict[str, str]:
    """Create access and refresh JWTs for the same user."""
    return {
        "access": create_token(
            subject, "access", timedelta(minutes=settings.access_token_expire_minutes)
        ),
        "refresh": create_token(
            subject, "refresh", timedelta(days=settings.refresh_token_expire_days)
        ),
        "token_type": "bearer",
    }
