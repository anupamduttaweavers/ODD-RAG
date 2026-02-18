"""FTP/FTPS adapter using Python's built-in ``ftplib``."""

import logging
import os
from ftplib import FTP, FTP_TLS, error_perm
from typing import Any, Dict, List, Optional, Set

from app.filesource.adapters.base import FileSourceAdapter

logger = logging.getLogger("app.filesource")


class FTPAdapter(FileSourceAdapter):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.port = self.port or 21
        self._ftp: Optional[FTP] = None

    def _connect(self) -> None:
        if not self.host:
            raise ValueError("Host is required for FTP connections")
        ftp: FTP = FTP_TLS()
        ftp.connect(self.host, self.port, timeout=self.timeout)

        if self.username:
            ftp.login(self.username, self.password or "")
        else:
            ftp.login()

        try:
            ftp.prot_p()
        except Exception:
            logger.debug("[FILESOURCE:%s] PROT P not supported, continuing", self.name)

        self._ftp = ftp

    def _disconnect(self) -> None:
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                try:
                    self._ftp.close()
                except Exception:
                    pass
            self._ftp = None

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
            self._ftp.cwd(self.base_path)
            result["directory_access"] = True
        except error_perm as exc:
            result["message"] = f"Cannot access directory: {exc}"
            self._disconnect()
            return result

        try:
            self._ftp.nlst()
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
            self._ftp.cwd(path)
            entries: List[Dict[str, Any]] = []
            self._ftp.retrlines("LIST", lambda line: entries.append(self._parse_list_line(line, path)))
        except Exception:
            return

        for entry in entries:
            if entry.get("is_dir"):
                self._walk_remote(entry["path"], extensions, out, base)
            elif any(entry["name"].lower().endswith(ext) for ext in extensions):
                rel = entry["path"]
                if rel.startswith(base):
                    rel = rel[len(base):].lstrip("/")
                out.append({
                    "name": entry["name"],
                    "path": entry["path"],
                    "relative_path": rel,
                    "size": entry.get("size", 0),
                })

    @staticmethod
    def _parse_list_line(line: str, parent: str) -> Dict[str, Any]:
        parts = line.split(None, 8)
        is_dir = line.startswith("d")
        name = parts[-1] if len(parts) >= 9 else line.strip()
        try:
            size = int(parts[4]) if len(parts) >= 9 else 0
        except (ValueError, IndexError):
            size = 0
        return {
            "name": name,
            "path": f"{parent.rstrip('/')}/{name}",
            "is_dir": is_dir,
            "size": size,
        }

    def _download_file(self, remote_path: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        dir_part = "/".join(remote_path.replace("\\", "/").split("/")[:-1])
        filename = remote_path.replace("\\", "/").split("/")[-1]
        self._ftp.cwd(dir_part)
        with open(local_path, "wb") as fh:
            self._ftp.retrbinary(f"RETR {filename}", fh.write)
