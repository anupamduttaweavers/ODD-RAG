"""
API Router for the Sync Management Module.

Endpoints:
    POST /trigger      — Force immediate synchronization
    POST /schedule     — Schedule sync at a specific IST datetime
    PUT  /interval     — Adjust the background sync interval
    GET  /status       — View current sync state and next execution time
    POST /failsafe     — Robust fail-safe sync with retry + fallback
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.sync_manager.schemas import (
    FailsafeSyncResponse,
    IntervalUpdateResponse,
    ScheduleSyncRequest,
    ScheduleSyncResponse,
    SyncResultResponse,
    SyncStatusResponse,
    UpdateIntervalRequest,
)
from app.sync_manager.service import sync_manager

router = APIRouter()


# ------------------------------------------------------------------
# POST /trigger — Force immediate synchronization
# ------------------------------------------------------------------
@router.post(
    "/trigger",
    response_model=SyncResultResponse,
    summary="Force immediate sync",
    description="Trigger a synchronization cycle immediately. "
    "Returns the full sync result including file counts and duration.",
)
async def trigger_sync():
    """Execute an immediate document synchronization."""
    logger.info("[SYNC_API] Trigger sync requested")
    try:
        result = await sync_manager.trigger_sync()
        status_code = status.HTTP_200_OK if result["success"] else status.HTTP_409_CONFLICT
        return JSONResponse(content=result, status_code=status_code)
    except Exception as exc:
        logger.error(f"[SYNC_API] Trigger sync error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Internal error during sync trigger: {exc}",
            },
        )


# ------------------------------------------------------------------
# POST /schedule — Schedule sync at a specific IST datetime
# ------------------------------------------------------------------
@router.post(
    "/schedule",
    response_model=ScheduleSyncResponse,
    summary="Schedule sync at IST datetime",
    description="Schedule a one-time synchronization at the provided IST datetime. "
    "Format: YYYY-MM-DD HH:MM:SS.  All times are interpreted as IST (UTC+05:30).",
)
async def schedule_sync(request: ScheduleSyncRequest):
    """Schedule a synchronization for a future IST datetime."""
    logger.info(f"[SYNC_API] Schedule sync requested for {request.scheduled_time}")
    try:
        result = await sync_manager.schedule_sync(request.scheduled_time)
        if not result["success"]:
            return JSONResponse(
                content=result,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except Exception as exc:
        logger.error(f"[SYNC_API] Schedule sync error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Internal error during sync scheduling: {exc}",
            },
        )


# ------------------------------------------------------------------
# PUT /interval — Adjust the background sync interval
# ------------------------------------------------------------------
@router.put(
    "/interval",
    response_model=IntervalUpdateResponse,
    summary="Update background sync interval",
    description="Change the interval (in seconds) at which the existing background "
    "sync job runs. Minimum: 30s, Maximum: 86400s (24h).",
)
async def update_interval(request: UpdateIntervalRequest):
    """Adjust the SYNC_INTERVAL_SECONDS at runtime."""
    logger.info(f"[SYNC_API] Interval update requested: {request.interval_seconds}s")
    try:
        result = sync_manager.update_interval(request.interval_seconds)
        if not result["success"]:
            return JSONResponse(
                content=result,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except Exception as exc:
        logger.error(f"[SYNC_API] Interval update error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Internal error during interval update: {exc}",
            },
        )


# ------------------------------------------------------------------
# GET /status — View current sync state
# ------------------------------------------------------------------
@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Get sync status",
    description="Returns the current sync state including running status, "
    "configured interval, next auto/scheduled sync time (IST), "
    "and last sync result.",
)
async def get_sync_status():
    """Retrieve the current synchronization status."""
    try:
        return JSONResponse(
            content=sync_manager.get_status(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error(f"[SYNC_API] Status check error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Internal error fetching sync status: {exc}",
            },
        )


# ------------------------------------------------------------------
# POST /failsafe — Robust fail-safe sync
# ------------------------------------------------------------------
@router.post(
    "/failsafe",
    response_model=FailsafeSyncResponse,
    summary="Fail-safe sync with retry",
    description="Execute a robust synchronization with automatic retry (up to 3 attempts, "
    "exponential backoff) and a lightweight fallback (registry-only sync) if all "
    "attempts fail. Designed to succeed even when the primary sync pipeline "
    "encounters transient errors.",
)
async def failsafe_sync():
    """
    Professional-grade fail-safe synchronization endpoint.

    - 3 retry attempts with exponential backoff (2s, 4s, 8s)
    - Falls back to registry-only sync on total failure
    - Full structured error reporting
    - Safe to call at any time without crashing the system
    """
    logger.info("[SYNC_API] Failsafe sync requested")
    try:
        result = await sync_manager.failsafe_sync()
        status_code = status.HTTP_200_OK if result["success"] else status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(content=result, status_code=status_code)
    except Exception as exc:
        logger.error(f"[SYNC_API] Failsafe sync error: {exc}", exc_info=True)
        return JSONResponse(
            content={
                "success": False,
                "message": f"Critical failure in failsafe endpoint: {exc}",
                "attempts": 0,
                "errors": [str(exc)],
                "fallback_used": False,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
