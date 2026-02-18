"""
Adapter factory — maps a protocol name to its concrete adapter class.

Usage::

    adapter = create_adapter({"protocol": "sftp", "host": "10.0.0.1", ...})
    async with adapter:
        files = await adapter.list_files({".pdf", ".txt"})
"""

import logging
from typing import Any, Dict

from app.filesource.adapters.base import FileSourceAdapter

logger = logging.getLogger("app.filesource")


def create_adapter(config: Dict[str, Any]) -> FileSourceAdapter:
    """
    Instantiate the correct adapter for the given *config* dict.

    Raises ``ValueError`` for unknown protocols and ``ImportError``
    if the required third-party library is not installed.
    """
    protocol = config.get("protocol", "").lower()

    if protocol == "local":
        from app.filesource.adapters.local import LocalFileAdapter
        return LocalFileAdapter(config)

    if protocol == "sftp":
        from app.filesource.adapters.sftp import SFTPAdapter
        return SFTPAdapter(config)

    if protocol == "smb":
        from app.filesource.adapters.smb import SMBAdapter
        return SMBAdapter(config)

    if protocol == "nfs":
        from app.filesource.adapters.nfs import NFSAdapter
        return NFSAdapter(config)

    if protocol == "ftp":
        from app.filesource.adapters.ftp import FTPAdapter
        return FTPAdapter(config)

    raise ValueError(
        f"Unsupported protocol: '{protocol}'. "
        f"Supported: local, sftp, smb, nfs, ftp"
    )
