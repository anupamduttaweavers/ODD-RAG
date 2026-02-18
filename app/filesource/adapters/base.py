"""
Abstract base class for all file-source adapters.

Concrete adapters implement the blocking ``_*`` methods; the public
async wrappers run them in a thread-pool so the event loop is never
blocked.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("app.filesource")


class FileSourceAdapter(ABC):
    """
    Protocol-agnostic interface for remote / local file sources.

    Lifecycle:
        adapter = SomeAdapter(config)
        await adapter.connect()
        result = await adapter.validate()
        files  = await adapter.list_files({".pdf", ".txt"})
        await adapter.download_file(remote, local)
        await adapter.disconnect()
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.name: str = config.get("name", "unnamed")
        self.host: Optional[str] = config.get("host")
        self.port: Optional[int] = config.get("port")
        self.base_path: str = config.get("base_path", "")
        self.username: Optional[str] = config.get("username")
        self.password: Optional[str] = config.get("password")
        self.key_file_path: Optional[str] = config.get("key_file_path")
        self.passphrase: Optional[str] = config.get("passphrase")
        self.auth_type: str = config.get("auth_type", "none")
        self.timeout: int = config.get("timeout_seconds", 30)
        self.max_retries: int = config.get("max_retries", 3)
        self.share_name: Optional[str] = config.get("share_name")
        self.domain: Optional[str] = config.get("domain")
        self._connected: bool = False

    # ── Abstract (blocking) methods implemented by subclasses ──

    @abstractmethod
    def _connect(self) -> None:
        """Establish the connection (blocking)."""

    @abstractmethod
    def _disconnect(self) -> None:
        """Close the connection (blocking)."""

    @abstractmethod
    def _validate(self) -> Dict[str, Any]:
        """
        Return a dict of check results, e.g.::

            {"authentication": True, "directory_access": True,
             "read_permission": True, "message": "All checks passed"}
        """

    @abstractmethod
    def _list_files(self, extensions: Set[str]) -> List[Dict[str, Any]]:
        """
        Return a list of dicts describing each matching file::

            [{"name": "report.pdf", "path": "/data/report.pdf",
              "size": 204800}]
        """

    @abstractmethod
    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download *remote_path* to *local_path* (blocking)."""

    # ── Async wrappers ────────────────────────────────────

    async def connect(self) -> None:
        await asyncio.to_thread(self._connect)
        self._connected = True
        logger.info("[FILESOURCE:%s] Connected", self.name)

    async def disconnect(self) -> None:
        try:
            await asyncio.to_thread(self._disconnect)
        except Exception as exc:
            logger.warning("[FILESOURCE:%s] Disconnect error: %s", self.name, exc)
        finally:
            self._connected = False

    async def validate(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._validate)

    async def list_files(self, extensions: Set[str]) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._list_files, extensions)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        await asyncio.to_thread(self._download_file, remote_path, local_path)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # Context-manager support for safe resource cleanup
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
