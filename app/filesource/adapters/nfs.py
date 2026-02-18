"""
NFS adapter — validates OS-level NFS mount points.

NFS shares are mounted via the operating system (``/etc/fstab`` or
``mount -t nfs``).  This adapter treats them as local directories and
adds a mount-presence check on top.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set

from app.filesource.adapters.local import LocalFileAdapter

logger = logging.getLogger("app.filesource")


class NFSAdapter(LocalFileAdapter):
    """Extends LocalFileAdapter with NFS-mount validation."""

    def _validate(self) -> Dict[str, Any]:
        result = super()._validate()
        result["nfs_mounted"] = self._is_nfs_mounted()
        if not result["nfs_mounted"]:
            result["message"] = (
                "Path is accessible but does not appear to be an NFS mount. "
                "Ensure the NFS share is mounted at this path."
            )
        return result

    @staticmethod
    def _is_nfs_mounted() -> bool:
        """
        Best-effort check by parsing ``/proc/mounts`` (Linux) or
        running ``mount``.
        """
        try:
            mounts_path = Path("/proc/mounts")
            if mounts_path.exists():
                text = mounts_path.read_text()
                return "nfs" in text.lower()
            out = subprocess.check_output(
                ["mount"], timeout=5, stderr=subprocess.DEVNULL
            )
            return "nfs" in out.decode().lower()
        except Exception:
            return False
