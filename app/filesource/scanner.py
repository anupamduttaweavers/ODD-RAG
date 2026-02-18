"""
Direct scan-and-vectorize engine for file sources.

Reads files **directly** from the source path (local, NFS, mounted SMB)
and feeds them through the existing processing pipeline — no file
copying to BASE_DATA_FOLDER required.

For truly remote protocols (SFTP, FTP, unmounted SMB) a temporary
download is used; temp files are cleaned up after vectorization.

The auto-scan job is registered on the **existing** APScheduler so it
runs on the same interval as the BASE_DATA_FOLDER sync.  When the
admin changes the interval via ``/chat/admin``, both jobs are
rescheduled together.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set

from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import select

from app.filesource import crypto
from app.filesource.adapters.registry import create_adapter
from app.filesource.database import get_session
from app.filesource.models import DEFAULT_PORTS, FileSourceConfig

logger = logging.getLogger("app.filesource")

_ALLOWED_EXT: Set[str] = {".pdf", ".txt"}
FILESOURCE_JOB_ID = "filesource-auto-scan"


# ── Direct scan (single source) ──────────────────────────

async def scan_and_vectorize(source_id: int) -> Dict[str, Any]:
    """
    Scan files at the source path and vectorize them in-place.

    For local / NFS / mounted paths the files are read directly —
    nothing is copied.  For SFTP / FTP / SMB the files are downloaded
    to a temporary directory, processed, then the temp files are
    removed.
    """
    session = get_session()
    try:
        src = session.get(FileSourceConfig, source_id)
        if not src:
            return _result(False, source_id, "", "Source not found")
        if not src.is_enabled:
            return _result(False, source_id, src.name, "Source is disabled")

        protocol = src.protocol
        is_local_path = protocol in ("local", "nfs")

        if is_local_path:
            return await _scan_local_path(src)
        else:
            return await _scan_remote_via_temp(src, session)
    except Exception as exc:
        logger.error("[SCANNER] scan_and_vectorize error: %s", exc, exc_info=True)
        return _result(False, source_id, "", f"Scan error: {exc}")
    finally:
        session.close()


async def _scan_local_path(src: FileSourceConfig) -> Dict[str, Any]:
    """Directly scan a locally-accessible path — zero file copying."""
    from app.core.hash_database import init_hash_db
    from app.utils.document_converstion import process_file
    from app.utils.hash_registry import (
        calculate_hash_from_file,
        lookup_hash,
        register_hash,
        update_processing_status,
    )
    from app.vectorstore.operations import add_documents
    from app.vectorstore.vectorstore import save_vectorstore, vector_store

    init_hash_db()
    base = Path(src.base_path)
    if not base.exists() or not base.is_dir():
        return _result(False, src.id, src.name, f"Path not accessible: {src.base_path}")

    new_files = 0
    skipped = 0
    chunks_added = 0
    errors: List[str] = []

    for root, _dirs, files in os.walk(base):
        for fname in files:
            if not any(fname.lower().endswith(ext) for ext in _ALLOWED_EXT):
                continue
            fpath = os.path.join(root, fname)
            folder_name = Path(root).name or src.name

            try:
                content_hash = calculate_hash_from_file(fpath)
                lookup = lookup_hash(content_hash)
                if lookup.exists:
                    skipped += 1
                    continue

                register_hash(
                    content_hash=content_hash,
                    file_name=fname,
                    file_path=fpath,
                    folder_name=folder_name,
                    file_type=Path(fname).suffix.lower().lstrip("."),
                    file_size=os.path.getsize(fpath),
                    is_processed=False,
                )

                doc_info, chunks = process_file(file_path=fpath, folder_name=folder_name)
                if chunks:
                    await add_documents(chunks)
                    chunks_added += len(chunks)

                update_processing_status(
                    content_hash=content_hash, is_processed=True, chunk_count=len(chunks)
                )
                new_files += 1
            except Exception as exc:
                errors.append(f"{fname}: {exc}")
                logger.error("[SCANNER] Error processing %s: %s", fname, exc)

    if chunks_added > 0:
        save_vectorstore(vector_store)
        logger.info("[SCANNER] Vectorstore saved (%d chunks total)", vector_store.index.ntotal)

    msg = f"Scan complete: {new_files} new, {skipped} skipped, {chunks_added} chunks"
    if errors:
        msg += f", {len(errors)} errors"
    logger.info("[SCANNER] %s — source '%s'", msg, src.name)

    return {
        "success": True,
        "source_id": src.id,
        "source_name": src.name,
        "new_files": new_files,
        "skipped": skipped,
        "chunks_added": chunks_added,
        "errors": errors,
        "message": msg,
        "mode": "direct",
    }


async def _scan_remote_via_temp(src: FileSourceConfig, session) -> Dict[str, Any]:
    """
    For truly remote sources: download to temp dir, vectorize, clean up.

    The temp files are deleted after processing — nothing permanent is
    stored on the local system except the vectors in FAISS.
    """
    from app.core.hash_database import init_hash_db
    from app.utils.document_converstion import process_file
    from app.utils.hash_registry import (
        calculate_hash_from_file,
        lookup_hash,
        register_hash,
        update_processing_status,
    )
    from app.vectorstore.operations import add_documents
    from app.vectorstore.vectorstore import save_vectorstore, vector_store

    init_hash_db()
    adapter_cfg = _build_config(src)

    try:
        adapter = create_adapter(adapter_cfg)
    except (ValueError, ImportError) as exc:
        return _result(False, src.id, src.name, f"Adapter error: {exc}")

    new_files = 0
    skipped = 0
    chunks_added = 0
    errors: List[str] = []

    with tempfile.TemporaryDirectory(prefix="filesource_scan_") as tmpdir:
        try:
            async with adapter:
                remote_files = await adapter.list_files(_ALLOWED_EXT)
                logger.info("[SCANNER] Remote '%s': %d files found", src.name, len(remote_files))

                for rf in remote_files:
                    local_tmp = os.path.join(tmpdir, rf["relative_path"])
                    try:
                        await adapter.download_file(rf["path"], local_tmp)

                        content_hash = calculate_hash_from_file(local_tmp)
                        lookup = lookup_hash(content_hash)
                        if lookup.exists:
                            skipped += 1
                            continue

                        folder_name = src.name
                        stable_path = f"remote://{src.name}/{rf['relative_path']}"

                        register_hash(
                            content_hash=content_hash,
                            file_name=rf["name"],
                            file_path=stable_path,
                            folder_name=folder_name,
                            file_type=Path(rf["name"]).suffix.lower().lstrip("."),
                            file_size=rf.get("size", 0),
                            is_processed=False,
                        )

                        doc_info, chunks = process_file(
                            file_path=local_tmp, folder_name=folder_name
                        )
                        if chunks:
                            await add_documents(chunks)
                            chunks_added += len(chunks)

                        update_processing_status(
                            content_hash=content_hash, is_processed=True, chunk_count=len(chunks)
                        )
                        new_files += 1
                    except Exception as exc:
                        errors.append(f"{rf['name']}: {exc}")
                        logger.error("[SCANNER] Remote scan error %s: %s", rf["name"], exc)

        except Exception as exc:
            logger.error("[SCANNER] Remote scan failed '%s': %s", src.name, exc, exc_info=True)
            return _result(False, src.id, src.name, f"Remote scan failed: {exc}", errors=errors)

    if chunks_added > 0:
        save_vectorstore(vector_store)
        logger.info("[SCANNER] Vectorstore saved (%d chunks total)", vector_store.index.ntotal)

    msg = f"Scan complete: {new_files} new, {skipped} skipped, {chunks_added} chunks"
    if errors:
        msg += f", {len(errors)} errors"
    logger.info("[SCANNER] %s — remote source '%s'", msg, src.name)

    return {
        "success": True,
        "source_id": src.id,
        "source_name": src.name,
        "new_files": new_files,
        "skipped": skipped,
        "chunks_added": chunks_added,
        "errors": errors,
        "message": msg,
        "mode": "remote_temp",
    }


# ── Auto-scan (runs on the EXISTING scheduler) ───────────

async def _auto_scan_all_enabled():
    """
    Scheduled job: scan every enabled source.

    Runs on the same APScheduler and interval as the BASE_DATA_FOLDER
    sync so that one interval governs all scanning.
    """
    session = get_session()
    try:
        sources = session.exec(
            select(FileSourceConfig).where(
                FileSourceConfig.is_enabled == True,  # noqa: E712
            )
        ).all()

        if not sources:
            return

        logger.info("[SCANNER] Auto-scan cycle: %d enabled source(s)", len(sources))
        for src in sources:
            try:
                result = await scan_and_vectorize(src.id)
                logger.info("[SCANNER] Auto-scan '%s': %s", src.name, result.get("message"))
            except Exception as exc:
                logger.error("[SCANNER] Auto-scan error '%s': %s", src.name, exc)
        logger.info("[SCANNER] Auto-scan cycle complete")
    except Exception as exc:
        logger.error("[SCANNER] Auto-scan cycle error: %s", exc, exc_info=True)
    finally:
        session.close()


def register_filesource_scan_job() -> None:
    """
    Add the file-source scan job to the **existing** scheduler.

    Call this after ``start_scheduler()`` so the scheduler is already
    running.  The job uses the same interval as ``SYNC_INTERVAL_SECONDS``
    so both BASE_DATA_FOLDER and file-source scans happen together.
    """
    from app.core.config import settings
    from app.core.scheduler import scheduler as existing_scheduler

    existing_scheduler.add_job(
        _auto_scan_all_enabled,
        trigger=IntervalTrigger(seconds=settings.SYNC_INTERVAL_SECONDS),
        id=FILESOURCE_JOB_ID,
        name="File Source Auto-Scan",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "[SCANNER] Registered on existing scheduler (interval=%ds)",
        settings.SYNC_INTERVAL_SECONDS,
    )


# ── Helpers ───────────────────────────────────────────────

def _build_config(src: FileSourceConfig) -> Dict[str, Any]:
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


def _result(success, source_id, name, msg, errors=None):
    return {
        "success": success,
        "source_id": source_id,
        "source_name": name,
        "new_files": 0,
        "skipped": 0,
        "chunks_added": 0,
        "errors": errors or [],
        "message": msg,
        "mode": "none",
    }
