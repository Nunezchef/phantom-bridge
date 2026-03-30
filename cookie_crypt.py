"""
Cookie encryption utility — Fernet-based encrypt/decrypt for cookie data at rest.

Cookies are stored as per-domain JSON files in data/cookies/<domain>.json.
Cookie *values* are encrypted; names and metadata remain in plaintext so
A0 can inspect cookie structure without decrypting.

The symmetric key is auto-generated on first use and stored at data/.cookie_key.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger("phantom_bridge")

_plugin_root = Path(__file__).resolve().parent
_KEY_FILE = _plugin_root / "data" / ".cookie_key"
_COOKIES_DIR = _plugin_root / "data" / "cookies"

# Module-level cache so we don't re-read the key file on every call
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return a cached Fernet instance, generating a key if none exists."""
    global _fernet
    if _fernet is not None:
        return _fernet

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        _KEY_FILE.write_bytes(key)
        logger.info("cookie_crypt: generated new encryption key at %s", _KEY_FILE)

    _fernet = Fernet(key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a single string value, returning a URL-safe base64 token."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_value(token: str) -> str:
    """Decrypt a single Fernet token back to the original string."""
    return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")


# ------------------------------------------------------------------
# Per-domain read / write
# ------------------------------------------------------------------

def save_domain_cookies(domain: str, cookies: list[dict]) -> Path:
    """Encrypt cookie values and write to data/cookies/<domain>.json.

    Each cookie dict keeps all fields in plaintext except 'value',
    which is replaced with 'encrypted_value'.

    Returns the path to the written file.
    """
    _COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = []
    for c in cookies:
        entry = {k: v for k, v in c.items() if k != "value"}
        entry["encrypted_value"] = encrypt_value(c.get("value", ""))
        encrypted.append(entry)

    file_path = _COOKIES_DIR / f"{domain}.json"
    file_path.write_text(
        json.dumps(encrypted, indent=2, default=str), encoding="utf-8"
    )
    return file_path


def load_domain_cookies(domain: str, *, decrypt: bool = False) -> list[dict]:
    """Read cookies for a domain from data/cookies/<domain>.json.

    If decrypt=True, replaces 'encrypted_value' with plaintext 'value'.
    If decrypt=False, returns cookies with 'encrypted_value' intact
    (useful for inspecting structure without exposing secrets).
    """
    file_path = _COOKIES_DIR / f"{domain}.json"
    if not file_path.exists():
        return []

    cookies = json.loads(file_path.read_text(encoding="utf-8"))

    if decrypt:
        for c in cookies:
            token = c.pop("encrypted_value", None)
            if token:
                c["value"] = decrypt_value(token)

    return cookies


def list_cookie_domains() -> list[str]:
    """Return all domains that have stored cookie files."""
    if not _COOKIES_DIR.exists():
        return []
    return sorted(f.stem for f in _COOKIES_DIR.glob("*.json"))


def delete_domain_cookies(domain: str) -> bool:
    """Delete the cookie file for a domain. Returns True if file existed."""
    file_path = _COOKIES_DIR / f"{domain}.json"
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def delete_all_cookies() -> int:
    """Delete all per-domain cookie files. Returns count of files removed."""
    if not _COOKIES_DIR.exists():
        return 0
    files = list(_COOKIES_DIR.glob("*.json"))
    for f in files:
        f.unlink()
    return len(files)


def get_cookie_summary() -> dict[str, dict]:
    """Return a summary of stored cookies per domain (no decryption).

    Returns: {"example.com": {"count": 5, "names": ["sid", "csrf", ...]}, ...}
    """
    summary = {}
    for domain in list_cookie_domains():
        cookies = load_domain_cookies(domain, decrypt=False)
        summary[domain] = {
            "count": len(cookies),
            "names": [c.get("name", "") for c in cookies],
        }
    return summary
