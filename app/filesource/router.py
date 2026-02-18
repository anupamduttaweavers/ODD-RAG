"""
API Router for the File Source Configuration module.

All endpoints return structured JSON with ``success``, ``message``,
``error_code``, and ``timestamp`` fields.

Endpoints:
    POST   /                 — Create a new file source
    GET    /                 — List all file sources
    GET    /{source_id}      — Get a single source
    PUT    /{source_id}      — Update a source
    DELETE /{source_id}      — Delete a source
    POST   /{source_id}/test — Test connection
    POST   /{source_id}/pull — Pull files to BASE_DATA_FOLDER
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.filesource import service
from app.filesource.schemas import (
    CreateFileSourceRequest,
    UpdateFileSourceRequest,
)

logger = logging.getLogger("app.filesource")
router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _ts() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _ok(data, msg="OK", code=status.HTTP_200_OK):
    return JSONResponse(
        {"success": True, "message": msg, "timestamp": _ts(), "data": data},
        status_code=code,
    )


def _err(msg, error_code="ERROR", http_code=status.HTTP_400_BAD_REQUEST):
    return JSONResponse(
        {
            "success": False,
            "message": msg,
            "error_code": error_code,
            "error_message": msg,
            "timestamp": _ts(),
        },
        status_code=http_code,
    )


# ── CRUD ──────────────────────────────────────────────────


@router.post(
    "/",
    summary="Create file source",
    description="Register a new file source configuration with encrypted credentials.",
    status_code=status.HTTP_201_CREATED,
)
async def create_file_source(request: CreateFileSourceRequest):
    logger.info("[FILESOURCE_API] Create source: %s", request.name)
    try:
        result = service.create_source(request.model_dump())
        if not result["success"]:
            return _err(result["message"], "CREATE_FAILED")
        return JSONResponse(
            {"success": True, "message": result["message"], "timestamp": _ts(), "data": result.get("source")},
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        logger.error("[FILESOURCE_API] Create error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get(
    "/",
    summary="List all file sources",
    description="Return every registered file source (credentials are masked).",
)
async def list_file_sources():
    try:
        sources = service.list_sources()
        return _ok({"sources": sources, "total": len(sources)})
    except Exception as exc:
        logger.error("[FILESOURCE_API] List error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get(
    "/{source_id}",
    summary="Get a file source",
)
async def get_file_source(source_id: int):
    try:
        src = service.get_source(source_id)
        if not src:
            return _err(f"Source id={source_id} not found", "NOT_FOUND", status.HTTP_404_NOT_FOUND)
        return _ok(src)
    except Exception as exc:
        logger.error("[FILESOURCE_API] Get error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/{source_id}",
    summary="Update a file source",
    description="Partial update — only provided fields are changed. "
    "Send password/passphrase only when changing them.",
)
async def update_file_source(source_id: int, request: UpdateFileSourceRequest):
    logger.info("[FILESOURCE_API] Update source id=%s", source_id)
    try:
        payload = {k: v for k, v in request.model_dump().items() if v is not None}
        if not payload:
            return _err("No fields to update", "EMPTY_UPDATE")
        result = service.update_source(source_id, payload)
        if not result["success"]:
            return _err(result["message"], "UPDATE_FAILED")
        return _ok(result.get("source"), result["message"])
    except Exception as exc:
        logger.error("[FILESOURCE_API] Update error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete(
    "/{source_id}",
    summary="Delete a file source",
)
async def delete_file_source(source_id: int):
    logger.info("[FILESOURCE_API] Delete source id=%s", source_id)
    try:
        result = service.delete_source(source_id)
        if not result["success"]:
            return _err(result["message"], "DELETE_FAILED", status.HTTP_404_NOT_FOUND)
        return _ok(None, result["message"])
    except Exception as exc:
        logger.error("[FILESOURCE_API] Delete error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Connection testing ────────────────────────────────────


@router.post(
    "/{source_id}/test",
    summary="Test file source connection",
    description="Validates authentication, directory access, and read permissions. "
    "Rate-limited to 1 test per 5 seconds per source.",
)
async def test_file_source(source_id: int):
    logger.info("[FILESOURCE_API] Test connection id=%s", source_id)
    try:
        result = await service.test_connection(source_id)
        code = status.HTTP_200_OK if result["success"] else status.HTTP_422_UNPROCESSABLE_ENTITY
        return JSONResponse(content=result, status_code=code)
    except Exception as exc:
        logger.error("[FILESOURCE_API] Test error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── File pulling ──────────────────────────────────────────


@router.post(
    "/{source_id}/pull",
    summary="Pull files from source",
    description="Download documents from the remote source into "
    "BASE_DATA_FOLDER/<source_name>/.  The existing sync mechanism "
    "will then detect and vectorize them automatically.",
)
async def pull_files(source_id: int):
    logger.info("[FILESOURCE_API] Pull files id=%s", source_id)
    try:
        result = await service.pull_files(source_id)
        code = status.HTTP_200_OK if result["success"] else status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(content=result, status_code=code)
    except Exception as exc:
        logger.error("[FILESOURCE_API] Pull error: %s", exc, exc_info=True)
        return _err(f"Internal error: {exc}", "INTERNAL", status.HTTP_500_INTERNAL_SERVER_ERROR)
