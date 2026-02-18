"""Pydantic schemas for the Sync Management API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ScheduleSyncRequest(BaseModel):
    """Request body for scheduling a sync at a specific IST datetime."""

    scheduled_time: str = Field(
        ...,
        description="Datetime in IST format: YYYY-MM-DD HH:MM:SS",
        examples=["2026-02-18 15:30:00"],
    )

    @field_validator("scheduled_time")
    @classmethod
    def validate_datetime_format(cls, v: str) -> str:
        v = v.strip()
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(
                "Invalid datetime format. Required: YYYY-MM-DD HH:MM:SS "
                "(e.g. 2026-02-18 15:30:00). All times are interpreted as IST."
            )
        if parsed.year < 2020 or parsed.year > 2100:
            raise ValueError("Year must be between 2020 and 2100.")
        return v


class UpdateIntervalRequest(BaseModel):
    """Request body for updating the background sync interval."""

    interval_seconds: int = Field(
        ...,
        gt=1,
        le=86400,
        description="New sync interval in seconds (min: 30, max: 86400)",
    )


class SyncResultResponse(BaseModel):
    """Structured response for a sync operation."""

    success: bool
    message: str
    sync_id: Optional[str] = None
    trigger_source: Optional[str] = None
    started_at_ist: Optional[str] = None
    completed_at_ist: Optional[str] = None
    duration_seconds: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    errors: Optional[List[Any]] = None


class SyncStatusResponse(BaseModel):
    """Response for the sync status endpoint."""

    status: str
    current_interval_seconds: int
    next_auto_sync_ist: Optional[str] = None
    next_scheduled_sync_ist: Optional[str] = None
    last_sync_result: Optional[SyncResultResponse] = None
    total_syncs_completed: int = 0
    total_syncs_failed: int = 0


class FailsafeSyncResponse(BaseModel):
    """Response for the fail-safe sync endpoint."""

    success: bool
    message: str
    attempts: int
    sync_result: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    fallback_used: bool = False


class IntervalUpdateResponse(BaseModel):
    """Response for interval update."""

    success: bool
    message: str
    old_interval_seconds: Optional[int] = None
    new_interval_seconds: Optional[int] = None


class ScheduleSyncResponse(BaseModel):
    """Response for schedule sync."""

    success: bool
    message: str
    scheduled_time_ist: Optional[str] = None
    delay_seconds: Optional[float] = None
