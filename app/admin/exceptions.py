"""Custom exception hierarchy for the admin module."""

from typing import Any, Optional


class AdminBaseException(Exception):
    """Base exception for all admin-related errors."""

    def __init__(self, message: str, error_code: str = "ADMIN_ERROR", detail: Optional[Any] = None):
        self.message = message
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)


class AuthenticationError(AdminBaseException):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message=message, error_code="AUTH_FAILED")


class TokenExpiredError(AdminBaseException):
    """Raised when a JWT token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, error_code="TOKEN_EXPIRED")


class TokenInvalidError(AdminBaseException):
    """Raised when a JWT token is malformed or invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, error_code="TOKEN_INVALID")


class InsufficientPermissionError(AdminBaseException):
    """Raised when user lacks required role/permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, error_code="FORBIDDEN")


class UserNotFoundError(AdminBaseException):
    """Raised when a referenced admin user does not exist."""

    def __init__(self, user_id: int):
        super().__init__(message=f"Admin user id={user_id} not found", error_code="USER_NOT_FOUND")


class UserAlreadyExistsError(AdminBaseException):
    """Raised when attempting to create a duplicate username."""

    def __init__(self, username: str):
        super().__init__(message=f"Username '{username}' already exists", error_code="USER_EXISTS")


class UserInactiveError(AdminBaseException):
    """Raised when an inactive user attempts to authenticate."""

    def __init__(self, message: str = "User account is deactivated"):
        super().__init__(message=message, error_code="USER_INACTIVE")
