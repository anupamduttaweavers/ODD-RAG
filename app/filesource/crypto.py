"""
Credential encryption for the File Source module.

Uses Fernet symmetric encryption (from the ``cryptography`` library that
ships with ``python-jose[cryptography]``).  A random key is generated on
first use and persisted to a file next to the project root.
"""

import logging
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("app.filesource")

_KEY_FILENAME = ".filesource.key"
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_KEY_PATH = _BASE_DIR / _KEY_FILENAME

_fernet: Fernet | None = None


def _load_or_create_key() -> bytes:
    if _KEY_PATH.exists():
        return _KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    _KEY_PATH.write_bytes(key)
    try:
        os.chmod(_KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    logger.info("[FILESOURCE] Encryption key generated at %s", _KEY_PATH)
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return the Fernet token as a UTF-8 string."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token. Returns empty string on invalid input."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception) as exc:
        logger.warning("[FILESOURCE] Decryption failed: %s", exc)
        return ""
