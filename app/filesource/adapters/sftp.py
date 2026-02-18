"""SFTP adapter using *paramiko* (optional dependency)."""

import logging
import os
import stat as stat_mod
from typing import Any, Dict, List, Set

from app.filesource.adapters.base import FileSourceAdapter

logger = logging.getLogger("app.filesource")

try:
    import paramiko  # type: ignore
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SFTPAdapter(FileSourceAdapter):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        if not PARAMIKO_AVAILABLE:
            raise ImportError(
                "paramiko is required for SFTP sources. "
                "Install it with: pip install paramiko"
            )
        self.port = self.port or 22
        self._transport: Any = None
        self._sftp: Any = None

    def _connect(self) -> None:
        if not self.host:
            raise ValueError("Host is required for SFTP connections")
        self._transport = paramiko.Transport((self.host, self.port))
        self._transport.banner_timeout = self.timeout
        self._transport.handshake_timeout = self.timeout

        if self.auth_type == "key" and self.key_file_path:
            pkey = paramiko.RSAKey.from_private_key_file(
                self.key_file_path,
                password=self.passphrase or None,
            )
            self._transport.connect(username=self.username or "", pkey=pkey)
        else:
            self._transport.connect(
                username=self.username or "",
                password=self.password or "",
            )
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        self._sftp.get_channel().settimeout(self.timeout)

    def _disconnect(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None

    def _validate(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "authentication": False,
            "directory_access": False,
            "read_permission": False,
            "message": "",
        }
        try:
            self._connect()
            result["authentication"] = True
        except Exception as exc:
            result["message"] = f"Authentication failed: {exc}"
            return result

        try:
            attrs = self._sftp.stat(self.base_path)
            if stat_mod.S_ISDIR(attrs.st_mode):
                result["directory_access"] = True
            else:
                result["message"] = f"Remote path is not a directory: {self.base_path}"
                return result
        except FileNotFoundError:
            result["message"] = f"Remote path does not exist: {self.base_path}"
            return result
        except Exception as exc:
            result["message"] = f"Cannot access remote path: {exc}"
            return result

        try:
            self._sftp.listdir(self.base_path)
            result["read_permission"] = True
            result["message"] = "All checks passed"
        except Exception as exc:
            result["message"] = f"Cannot list directory: {exc}"

        self._disconnect()
        return result

    def _list_files(self, extensions: Set[str]) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        self._walk_remote(self.base_path, extensions, files, self.base_path)
        return files

    def _walk_remote(
        self, path: str, extensions: Set[str],
        out: List[Dict[str, Any]], base: str,
    ) -> None:
        try:
            entries = self._sftp.listdir_attr(path)
        except Exception:
            return
        for entry in entries:
            full_path = f"{path.rstrip('/')}/{entry.filename}"
            if stat_mod.S_ISDIR(entry.st_mode):
                self._walk_remote(full_path, extensions, out, base)
            elif any(entry.filename.lower().endswith(ext) for ext in extensions):
                rel = full_path
                if full_path.startswith(base):
                    rel = full_path[len(base):].lstrip("/")
                out.append({
                    "name": entry.filename,
                    "path": full_path,
                    "relative_path": rel,
                    "size": entry.st_size or 0,
                })

    def _download_file(self, remote_path: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self._sftp.get(remote_path, local_path)
