"""Pydantic schemas for the File Source Configuration API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.filesource.models import SUPPORTED_PROTOCOLS


# ── Requests ──────────────────────────────────────────────

class CreateFileSourceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    protocol: str = Field(..., max_length=16)
    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    base_path: str = Field(..., min_length=1, max_length=1024)
    share_name: Optional[str] = Field(default=None, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=128)
    auth_type: str = Field(default="none", max_length=16)
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None)
    key_file_path: Optional[str] = Field(default=None, max_length=1024)
    passphrase: Optional[str] = Field(default=None)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    is_enabled: bool = Field(default=True)
    sync_to_base_folder: bool = Field(default=True)
    auto_scan_enabled: bool = Field(default=False)

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SUPPORTED_PROTOCOLS:
            raise ValueError(
                f"Unsupported protocol '{v}'. Supported: {', '.join(SUPPORTED_PROTOCOLS)}"
            )
        return v

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("none", "password", "key"):
            raise ValueError("auth_type must be one of: none, password, key")
        return v

    @field_validator("base_path")
    @classmethod
    def validate_base_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("Path traversal sequences (..) are not allowed")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError("Name may only contain letters, digits, spaces, hyphens, underscores")
        return v


class UpdateFileSourceRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    protocol: Optional[str] = Field(default=None, max_length=16)
    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    base_path: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    share_name: Optional[str] = Field(default=None, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=128)
    auth_type: Optional[str] = Field(default=None, max_length=16)
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None)
    key_file_path: Optional[str] = Field(default=None, max_length=1024)
    passphrase: Optional[str] = Field(default=None)
    timeout_seconds: Optional[int] = Field(default=None, ge=5, le=300)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    is_enabled: Optional[bool] = None
    sync_to_base_folder: Optional[bool] = None
    auto_scan_enabled: Optional[bool] = None

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in SUPPORTED_PROTOCOLS:
            raise ValueError(
                f"Unsupported protocol '{v}'. Supported: {', '.join(SUPPORTED_PROTOCOLS)}"
            )
        return v

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in ("none", "password", "key"):
            raise ValueError("auth_type must be one of: none, password, key")
        return v

    @field_validator("base_path")
    @classmethod
    def validate_base_path(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if ".." in v:
            raise ValueError("Path traversal sequences (..) are not allowed")
        return v.strip()


# ── Responses ─────────────────────────────────────────────

class FileSourceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    base_path: str
    share_name: Optional[str] = None
    domain: Optional[str] = None
    auth_type: str
    username: Optional[str] = None
    has_password: bool = False
    key_file_path: Optional[str] = None
    has_passphrase: bool = False
    timeout_seconds: int
    max_retries: int
    is_enabled: bool
    sync_to_base_folder: bool
    auto_scan_enabled: bool = False
    created_at: str
    updated_at: str
    last_tested_at: Optional[str] = None
    connection_status: str
    status_message: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    success: bool
    source_id: int
    source_name: str
    protocol: str
    checks: Dict[str, Any] = {}
    message: str
    timestamp: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class PullFilesResponse(BaseModel):
    success: bool
    source_id: int
    source_name: str
    files_downloaded: int = 0
    files_skipped: int = 0
    total_bytes: int = 0
    destination: str = ""
    errors: List[str] = []
    message: str
    timestamp: str


class FileSourceListResponse(BaseModel):
    sources: List[FileSourceResponse]
    total: int


class ApiResponse(BaseModel):
    success: bool
    message: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str
    data: Optional[Any] = None
