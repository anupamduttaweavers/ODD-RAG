"""SMB / CIFS adapter using *smbprotocol* (optional dependency)."""

import logging
import os
from typing import Any, Dict, List, Set

from app.filesource.adapters.base import FileSourceAdapter

logger = logging.getLogger("app.filesource")

try:
    import smbclient  # type: ignore
    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False


class SMBAdapter(FileSourceAdapter):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        if not SMB_AVAILABLE:
            raise ImportError(
                "smbprotocol is required for SMB sources. "
                "Install it with: pip install smbprotocol"
            )
        self.port = self.port or 445
        if not self.share_name:
            raise ValueError("share_name is required for SMB connections")
        self._registered = False

    @property
    def _unc_base(self) -> str:
        """Build \\\\host\\share\\path UNC string."""
        share = f"\\\\{self.host}\\{self.share_name}"
        if self.base_path and self.base_path.strip("/\\"):
            cleaned = self.base_path.strip("/\\").replace("/", "\\")
            share = f"{share}\\{cleaned}"
        return share

    def _connect(self) -> None:
        if not self.host:
            raise ValueError("Host is required for SMB connections")
        smbclient.register_session(
            self.host,
            username=self.username or "",
            password=self.password or "",
            port=self.port,
            connection_timeout=self.timeout,
        )
        self._registered = True

    def _disconnect(self) -> None:
        if self._registered and self.host:
            try:
                smbclient.delete_session(self.host, port=self.port)
            except Exception:
                pass
            self._registered = False

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
            info = smbclient.stat(self._unc_base)
            import stat as stat_mod
            if stat_mod.S_ISDIR(info.st_mode):
                result["directory_access"] = True
            else:
                result["message"] = f"Remote path is not a directory: {self._unc_base}"
                return result
        except Exception as exc:
            result["message"] = f"Cannot access remote path: {exc}"
            return result

        try:
            smbclient.listdir(self._unc_base)
            result["read_permission"] = True
            result["message"] = "All checks passed"
        except Exception as exc:
            result["message"] = f"Cannot list directory: {exc}"

        self._disconnect()
        return result

    def _list_files(self, extensions: Set[str]) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        self._walk_remote(self._unc_base, extensions, files, self._unc_base)
        return files

    def _walk_remote(
        self, path: str, extensions: Set[str],
        out: List[Dict[str, Any]], base: str,
    ) -> None:
        try:
            entries = smbclient.scandir(path)
        except Exception:
            return
        for entry in entries:
            if entry.name in (".", ".."):
                continue
            full = f"{path.rstrip(chr(92))}\\{entry.name}"
            if entry.is_dir():
                self._walk_remote(full, extensions, out, base)
            elif any(entry.name.lower().endswith(ext) for ext in extensions):
                rel = full
                if full.startswith(base):
                    rel = full[len(base):].lstrip("\\").replace("\\", "/")
                try:
                    size = entry.stat().st_size
                except Exception:
                    size = 0
                out.append({
                    "name": entry.name,
                    "path": full,
                    "relative_path": rel,
                    "size": size,
                })

    def _download_file(self, remote_path: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with smbclient.open_file(remote_path, mode="rb") as src:
            with open(local_path, "wb") as dst:
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    dst.write(chunk)
