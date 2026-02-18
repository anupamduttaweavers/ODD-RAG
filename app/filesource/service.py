"""
Business logic for File Source management.

Handles CRUD, connection testing, and file pulling — keeping
the router thin and adapters ignorant of persistence details.
"""

import logging
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlmodel import select

from app.filesource import crypto
from app.filesource.adapters.registry import create_adapter
from app.filesource.database import get_session
from app.filesource.models import DEFAULT_PORTS, FileSourceConfig

logger = logging.getLogger("app.filesource")

IST = timezone(timedelta(hours=5, minutes=30))
_ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".txt"}
_MIN_TEST_INTERVAL = 5
_last_test_ts: Dict[int, float] = {}


def _now_ist() -> datetime:
    return datetime.now(IST)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S IST")


def _to_safe_response(src: FileSourceConfig) -> Dict[str, Any]:
    """Convert a model instance to a dict safe for API responses."""
    return {
        "id": src.id,
        "name": src.name,
        "description": src.description,
        "protocol": src.protocol,
        "host": src.host,
        "port": src.port,
        "base_path": src.base_path,
        "share_name": src.share_name,
        "domain": src.domain,
        "auth_type": src.auth_type,
        "username": src.username,
        "has_password": bool(src.encrypted_password),
        "key_file_path": src.key_file_path,
        "has_passphrase": bool(src.encrypted_passphrase),
        "timeout_seconds": src.timeout_seconds,
        "max_retries": src.max_retries,
        "is_enabled": src.is_enabled,
        "sync_to_base_folder": src.sync_to_base_folder,
        "auto_scan_enabled": src.auto_scan_enabled,
        "created_at": src.created_at.isoformat() if src.created_at else "",
        "updated_at": src.updated_at.isoformat() if src.updated_at else "",
        "last_tested_at": src.last_tested_at.isoformat() if src.last_tested_at else None,
        "connection_status": src.connection_status,
        "status_message": src.status_message,
    }


def _build_adapter_config(src: FileSourceConfig) -> Dict[str, Any]:
    """Build the dict expected by adapter constructors, decrypting secrets."""
    return {
        "name": src.name,
        "protocol": src.protocol,
        "host": src.host,
        "port": src.port or DEFAULT_PORTS.get(src.protocol),
        "base_path": src.base_path,
        "share_name": src.share_name,
        "domain": src.domain,
        "auth_type": src.auth_type,
        "username": src.username,
        "password": crypto.decrypt(src.encrypted_password or ""),
        "key_file_path": src.key_file_path,
        "passphrase": crypto.decrypt(src.encrypted_passphrase or ""),
        "timeout_seconds": src.timeout_seconds,
        "max_retries": src.max_retries,
    }


# ── CRUD ──────────────────────────────────────────────────

def create_source(data: Dict[str, Any]) -> Dict[str, Any]:
    session = get_session()
    try:
        existing = session.exec(
            select(FileSourceConfig).where(FileSourceConfig.name == data["name"])
        ).first()
        if existing:
            return {"success": False, "message": f"Source named '{data['name']}' already exists"}

        now = datetime.utcnow()
        src = FileSourceConfig(
            name=data["name"],
            description=data.get("description"),
            protocol=data["protocol"],
            host=data.get("host"),
            port=data.get("port") or DEFAULT_PORTS.get(data["protocol"]),
            base_path=data["base_path"],
            share_name=data.get("share_name"),
            domain=data.get("domain"),
            auth_type=data.get("auth_type", "none"),
            username=data.get("username"),
            encrypted_password=crypto.encrypt(data["password"]) if data.get("password") else None,
            key_file_path=data.get("key_file_path"),
            encrypted_passphrase=crypto.encrypt(data["passphrase"]) if data.get("passphrase") else None,
            timeout_seconds=data.get("timeout_seconds", 30),
            max_retries=data.get("max_retries", 3),
            is_enabled=data.get("is_enabled", True),
            sync_to_base_folder=data.get("sync_to_base_folder", True),
            auto_scan_enabled=data.get("auto_scan_enabled", False),
            created_at=now,
            updated_at=now,
        )
        session.add(src)
        session.commit()
        session.refresh(src)
        logger.info("[FILESOURCE] Created source '%s' (id=%s, protocol=%s)", src.name, src.id, src.protocol)
        return {"success": True, "message": "File source created", "source": _to_safe_response(src)}
    except Exception as exc:
        session.rollback()
        logger.error("[FILESOURCE] Create failed: %s", exc, exc_info=True)
        return {"success": False, "message": f"Failed to create source: {exc}"}
    finally:
        session.close()


def update_source(source_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    session = get_session()
    try:
        src = session.get(FileSourceConfig, source_id)
        if not src:
            return {"success": False, "message": f"Source id={source_id} not found"}

        for field in (
            "name", "description", "protocol", "host", "port", "base_path",
            "share_name", "domain", "auth_type", "username", "key_file_path",
            "timeout_seconds", "max_retries", "is_enabled", "sync_to_base_folder",
            "auto_scan_enabled",
        ):
            if field in data and data[field] is not None:
                setattr(src, field, data[field])

        if "password" in data and data["password"] is not None:
            src.encrypted_password = crypto.encrypt(data["password"]) if data["password"] else None
        if "passphrase" in data and data["passphrase"] is not None:
            src.encrypted_passphrase = crypto.encrypt(data["passphrase"]) if data["passphrase"] else None

        src.updated_at = datetime.utcnow()
        session.add(src)
        session.commit()
        session.refresh(src)
        logger.info("[FILESOURCE] Updated source '%s' (id=%s)", src.name, src.id)
        return {"success": True, "message": "File source updated", "source": _to_safe_response(src)}
    except Exception as exc:
        session.rollback()
        logger.error("[FILESOURCE] Update failed: %s", exc, exc_info=True)
        return {"success": False, "message": f"Failed to update source: {exc}"}
    finally:
        session.close()


def delete_source(source_id: int) -> Dict[str, Any]:
    session = get_session()
    try:
        src = session.get(FileSourceConfig, source_id)
        if not src:
            return {"success": False, "message": f"Source id={source_id} not found"}
        name = src.name
        session.delete(src)
        session.commit()
        logger.info("[FILESOURCE] Deleted source '%s' (id=%s)", name, source_id)
        return {"success": True, "message": f"Source '{name}' deleted"}
    except Exception as exc:
        session.rollback()
        logger.error("[FILESOURCE] Delete failed: %s", exc, exc_info=True)
        return {"success": False, "message": f"Failed to delete source: {exc}"}
    finally:
        session.close()


def get_source(source_id: int) -> Optional[Dict[str, Any]]:
    session = get_session()
    try:
        src = session.get(FileSourceConfig, source_id)
        return _to_safe_response(src) if src else None
    finally:
        session.close()


def list_sources() -> List[Dict[str, Any]]:
    session = get_session()
    try:
        results = session.exec(select(FileSourceConfig).order_by(FileSourceConfig.name)).all()
        return [_to_safe_response(s) for s in results]
    finally:
        session.close()


# ── Connection testing ────────────────────────────────────

async def test_connection(source_id: int) -> Dict[str, Any]:
    """Full connection test: auth → directory access → read permissions."""
    now = time.monotonic()
    if source_id in _last_test_ts and (now - _last_test_ts[source_id]) < _MIN_TEST_INTERVAL:
        return {
            "success": False,
            "source_id": source_id,
            "source_name": "",
            "protocol": "",
            "checks": {},
            "message": "Rate limited — wait a few seconds between tests",
            "timestamp": _fmt(_now_ist()),
            "error_code": "RATE_LIMITED",
            "error_message": "Minimum interval between tests is 5 seconds",
        }
    _last_test_ts[source_id] = now

    session = get_session()
    try:
        src = session.get(FileSourceConfig, source_id)
        if not src:
            return {
                "success": False, "source_id": source_id, "source_name": "",
                "protocol": "", "checks": {},
                "message": f"Source id={source_id} not found",
                "timestamp": _fmt(_now_ist()), "error_code": "NOT_FOUND",
                "error_message": "Source not found",
            }

        adapter_cfg = _build_adapter_config(src)
        ts = _fmt(_now_ist())

        try:
            adapter = create_adapter(adapter_cfg)
        except (ValueError, ImportError) as exc:
            _update_status(session, src, "failed", str(exc))
            return {
                "success": False, "source_id": src.id, "source_name": src.name,
                "protocol": src.protocol, "checks": {},
                "message": str(exc), "timestamp": ts,
                "error_code": "ADAPTER_ERROR", "error_message": str(exc),
            }

        try:
            checks = await adapter.validate()
            success = all(
                checks.get(k) for k in ("authentication", "directory_access", "read_permission")
            )
            status = "success" if success else "failed"
            _update_status(session, src, status, checks.get("message", ""))
            return {
                "success": success,
                "source_id": src.id,
                "source_name": src.name,
                "protocol": src.protocol,
                "checks": checks,
                "message": checks.get("message", ""),
                "timestamp": ts,
                "error_code": None if success else "CHECK_FAILED",
                "error_message": None if success else checks.get("message"),
            }
        except Exception as exc:
            msg = f"Test error: {exc}"
            _update_status(session, src, "failed", msg)
            logger.error("[FILESOURCE] Test failed for '%s': %s", src.name, exc, exc_info=True)
            return {
                "success": False, "source_id": src.id, "source_name": src.name,
                "protocol": src.protocol, "checks": {},
                "message": msg, "timestamp": ts,
                "error_code": "EXCEPTION", "error_message": str(exc),
            }
    finally:
        session.close()


def _update_status(session, src: FileSourceConfig, status: str, message: str) -> None:
    src.connection_status = status
    src.status_message = message[:1024] if message else None
    src.last_tested_at = datetime.utcnow()
    session.add(src)
    session.commit()


# ── File pulling ──────────────────────────────────────────

async def pull_files(source_id: int) -> Dict[str, Any]:
    """
    Download documents from a remote source into ``BASE_DATA_FOLDER/<name>/``.

    The existing sync mechanism will then detect and vectorize them
    automatically — no changes to existing logic required.
    """
    session = get_session()
    ts = _fmt(_now_ist())
    try:
        src = session.get(FileSourceConfig, source_id)
        if not src:
            return {
                "success": False, "source_id": source_id, "source_name": "",
                "files_downloaded": 0, "files_skipped": 0, "total_bytes": 0,
                "destination": "", "errors": [], "message": "Source not found",
                "timestamp": ts,
            }
        if not src.is_enabled:
            return {
                "success": False, "source_id": src.id, "source_name": src.name,
                "files_downloaded": 0, "files_skipped": 0, "total_bytes": 0,
                "destination": "", "errors": [],
                "message": "Source is disabled — enable it before pulling files",
                "timestamp": ts,
            }

        from app.core.config import settings
        dest_dir = Path(settings.BASE_DATA_FOLDER) / src.name
        dest_dir.mkdir(parents=True, exist_ok=True)

        adapter_cfg = _build_adapter_config(src)
        downloaded = 0
        skipped = 0
        total_bytes = 0
        errors: List[str] = []

        try:
            adapter = create_adapter(adapter_cfg)
        except (ValueError, ImportError) as exc:
            return {
                "success": False, "source_id": src.id, "source_name": src.name,
                "files_downloaded": 0, "files_skipped": 0, "total_bytes": 0,
                "destination": str(dest_dir), "errors": [str(exc)],
                "message": f"Adapter error: {exc}", "timestamp": ts,
            }

        try:
            async with adapter:
                remote_files = await adapter.list_files(_ALLOWED_EXTENSIONS)
                logger.info(
                    "[FILESOURCE] Pull '%s': %d remote files found", src.name, len(remote_files)
                )

                for rf in remote_files:
                    local_target = dest_dir / rf["relative_path"]
                    if local_target.exists() and local_target.stat().st_size == rf.get("size", -1):
                        skipped += 1
                        continue
                    try:
                        await adapter.download_file(rf["path"], str(local_target))
                        downloaded += 1
                        total_bytes += rf.get("size", 0)
                    except Exception as exc:
                        errors.append(f"{rf['name']}: {exc}")
                        logger.error("[FILESOURCE] Download error %s: %s", rf["name"], exc)

            _update_status(session, src, "success", f"Pull OK: {downloaded} downloaded")
            msg = (
                f"Pull complete: {downloaded} downloaded, {skipped} skipped"
                + (f", {len(errors)} errors" if errors else "")
            )
            logger.info("[FILESOURCE] %s", msg)
            return {
                "success": True, "source_id": src.id, "source_name": src.name,
                "files_downloaded": downloaded, "files_skipped": skipped,
                "total_bytes": total_bytes, "destination": str(dest_dir),
                "errors": errors, "message": msg, "timestamp": ts,
            }
        except Exception as exc:
            _update_status(session, src, "failed", str(exc))
            logger.error("[FILESOURCE] Pull failed for '%s': %s", src.name, exc, exc_info=True)
            return {
                "success": False, "source_id": src.id, "source_name": src.name,
                "files_downloaded": downloaded, "files_skipped": skipped,
                "total_bytes": total_bytes, "destination": str(dest_dir),
                "errors": errors + [str(exc)], "message": f"Pull failed: {exc}",
                "timestamp": ts,
            }
    finally:
        session.close()
