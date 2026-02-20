"""SQLModel table definitions for admin users and activity logs."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class AdminUser(SQLModel, table=True):
    """Stores admin/superadmin accounts with Argon2-hashed passwords."""

    __tablename__ = "admin_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True, index=True)
    hashed_password: str
    role: str = Field(max_length=20, default="admin")  # "superadmin" | "admin"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(max_length=100, default="system")


class AdminActivityLog(SQLModel, table=True):
    """Immutable audit trail of every admin action."""

    __tablename__ = "admin_activity_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, index=True)
    action: str = Field(max_length=50, index=True)
    detail: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
