"""
Centralized data path resolver for Phantom Bridge.

All persistent data (cookies, playbooks, sitemaps, auth registry, encryption key)
lives under a single data root directory. This module provides a single source of
truth for resolving those paths.

Default data root: <plugin_root>/data/
Override via environment variable: PHANTOM_BRIDGE_DATA_DIR
Override via config: pass data_dir to functions that accept it.

Directory layout:
    data/
    ├── .cookie_key              # Fernet encryption key
    ├── cookies/                 # Per-domain encrypted cookie files
    │   ├── example.com.json
    │   └── ...
    ├── auth_registry.json       # Detected authenticated domains
    ├── sitemaps/                # Learned URL patterns per domain
    ├── playbooks/               # Recorded workflow JSON files
    └── profile/                 # Chromium user data (shared with A0)
"""

from __future__ import annotations

import os
from pathlib import Path

_plugin_root = Path(__file__).resolve().parent

# Environment variable override — set this to relocate the entire data tree.
# Example: PHANTOM_BRIDGE_DATA_DIR=/a0/usr/workdir/phantom
_env_override = os.environ.get("PHANTOM_BRIDGE_DATA_DIR", "").strip()

if _env_override:
    DATA_DIR = Path(_env_override)
else:
    DATA_DIR = _plugin_root / "data"


def get_data_dir() -> Path:
    return DATA_DIR


def get_key_file() -> Path:
    return DATA_DIR / ".cookie_key"


def get_cookies_dir() -> Path:
    return DATA_DIR / "cookies"


def get_auth_registry_file() -> Path:
    return DATA_DIR / "auth_registry.json"


def get_sitemaps_dir() -> Path:
    return DATA_DIR / "sitemaps"


def get_playbooks_dir() -> Path:
    return DATA_DIR / "playbooks"


def get_profile_dir() -> Path:
    return DATA_DIR / "profile"


def ensure_dirs() -> None:
    for d in [
        DATA_DIR,
        get_cookies_dir(),
        get_sitemaps_dir(),
        get_playbooks_dir(),
        get_profile_dir(),
    ]:
        d.mkdir(parents=True, exist_ok=True)
