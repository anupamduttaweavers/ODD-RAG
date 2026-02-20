"""Pydantic request / response models for the admin API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    expires_in_minutes: int


class MeResponse(BaseModel):
    username: str
    role: str
    is_active: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(default="admin")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "superadmin"):
            raise ValueError("Role must be 'admin' or 'superadmin'")
        return v


class UpdateUserRequest(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("admin", "superadmin"):
            raise ValueError("Role must be 'admin' or 'superadmin'")
        return v


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str


class UserListResponse(BaseModel):
    users: List[AdminUserOut]
    total: int


class ActivityLogOut(BaseModel):
    id: int
    username: str
    action: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime


class ActivityLogListResponse(BaseModel):
    logs: List[ActivityLogOut]
    total: int
    page: int
    page_size: int
