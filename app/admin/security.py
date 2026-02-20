"""Argon2 password hashing and JWT token utilities for the admin module.

Intentionally separate from app.core.security so existing bcrypt-based
auth remains untouched.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against an Argon2id *hashed* value."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


def create_admin_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Issue a JWT signed with the admin-specific secret."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ADMIN_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iss": "admin"})
    return jwt.encode(to_encode, settings.ADMIN_JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_admin_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate an admin JWT. Returns payload or None."""
    try:
        payload = jwt.decode(
            token,
            settings.ADMIN_JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("iss") != "admin":
            return None
        return payload
    except JWTError:
        return None
