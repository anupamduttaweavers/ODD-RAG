"""FastAPI dependency-injection callables for admin authentication.

Usage in routers:
    @router.get("/protected", dependencies=[Depends(require_admin)])
    async def protected_route(): ...

    @router.get("/super-only", dependencies=[Depends(require_superadmin)])
    async def super_only(): ...
"""

from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status

from app.admin.exceptions import (
    InsufficientPermissionError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.admin.security import decode_admin_token
from app.admin.service import get_user_by_username


def _extract_token(request: Request, admin_token: Optional[str] = Cookie(default=None)) -> str:
    """Pull the JWT from the Authorization header or the admin_token cookie."""
    if admin_token:
        return admin_token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Not authenticated", "error_code": "AUTH_REQUIRED"},
    )


def get_current_admin(request: Request, token: str = Depends(_extract_token)):
    """Validate the token and return the AdminUser row.

    Raises 401 on invalid/expired token or unknown user.
    """
    payload = decode_admin_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": TokenInvalidError().message, "error_code": "TOKEN_INVALID"},
        )

    username: str = payload.get("sub", "")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": TokenExpiredError().message, "error_code": "TOKEN_EXPIRED"},
        )

    user = get_user_by_username(username)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "User not found or inactive", "error_code": "AUTH_FAILED"},
        )
    return user


def require_admin(admin=Depends(get_current_admin)):
    """Dependency that simply ensures the caller is a valid admin."""
    return admin


def require_superadmin(admin=Depends(get_current_admin)):
    """Dependency that ensures the caller holds the superadmin role."""
    if admin.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": InsufficientPermissionError().message,
                "error_code": "FORBIDDEN",
            },
        )
    return admin
