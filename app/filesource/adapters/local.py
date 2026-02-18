"""Adapter for local / OS-mounted file systems (no external deps)."""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

from app.filesource.adapters.base import FileSourceAdapter

logger = logging.getLogger("app.filesource")


class LocalFileAdapter(FileSourceAdapter):

    def _connect(self) -> None:
        if not os.path.exists(self.base_path):
            raise FileNotFoundError(f"Path does not exist: {self.base_path}")

    def _disconnect(self) -> None:
        pass

    def _validate(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "authentication": True,
            "directory_access": False,
            "read_permission": False,
            "message": "",
        }
        p = Path(self.base_path)
        if not p.exists():
            result["message"] = f"Path does not exist: {self.base_path}"
            return result
        if not p.is_dir():
            result["message"] = f"Path is not a directory: {self.base_path}"
            return result
        result["directory_access"] = True

        if os.access(self.base_path, os.R_OK):
            result["read_permission"] = True
            result["message"] = "All checks passed"
        else:
            result["message"] = "Directory exists but is not readable"
        return result

    def _list_files(self, extensions: Set[str]) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        base = Path(self.base_path)
        if not base.exists():
            return files
        for root, _dirs, filenames in os.walk(base):
            for fname in filenames:
                if any(fname.lower().endswith(ext) for ext in extensions):
                    full = Path(root) / fname
                    try:
                        size = full.stat().st_size
                    except OSError:
                        size = 0
                    files.append({
                        "name": fname,
                        "path": str(full),
                        "relative_path": str(full.relative_to(base)),
                        "size": size,
                    })
        return files

    def _download_file(self, remote_path: str, local_path: str) -> None:
        if os.path.abspath(remote_path) == os.path.abspath(local_path):
            return
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(remote_path, local_path)
