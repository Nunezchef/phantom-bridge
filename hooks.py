"""Phantom Bridge — Framework lifecycle hooks."""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("phantom_bridge")

# Relative path from A0 root to this plugin's data directory.
# Used to ensure the profile dir (with Chromium Singleton files) is gitignored.
_PLUGIN_DATA_GITIGNORE = "usr/plugins/phantom_bridge/data/"


def _ensure_gitignore_entry(a0_root: Path) -> None:
    """Add the plugin's data dir to A0's root .gitignore if not already present.

    Chromium's profile directory creates SingletonLock/SingletonSocket/SingletonCookie
    files (Unix sockets & symlinks) that break git operations like ``git stash
    --include-untracked``.  A0's existing ``usr/**`` pattern *should* cover them,
    but adding an explicit entry is a defensive safeguard against gitignore changes.
    """
    gitignore = a0_root / ".gitignore"
    if not gitignore.exists():
        return

    content = gitignore.read_text()
    if _PLUGIN_DATA_GITIGNORE in content:
        return  # already present

    # Append the entry
    if not content.endswith("\n"):
        content += "\n"
    content += f"\n# Phantom Bridge — Chromium profile (sockets & locks break git stash)\n{_PLUGIN_DATA_GITIGNORE}\n"
    gitignore.write_text(content)
    logger.info("phantom_bridge: added %s to .gitignore", _PLUGIN_DATA_GITIGNORE)


def _cleanup_singleton_files(plugin_dir: Path) -> None:
    """Remove stale Chromium Singleton files from the profile directory.

    These files (symlinks / Unix sockets) are only valid while Chromium is
    running.  After a container restart or unclean shutdown they linger and
    can cause git errors or prevent Chromium from starting.
    """
    profile_dir = plugin_dir / "data" / "profile"
    if not profile_dir.exists():
        return

    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        path = profile_dir / name
        if path.is_symlink() or path.exists():
            try:
                path.unlink()
                logger.info("phantom_bridge: removed stale %s", name)
            except OSError as e:
                logger.warning("phantom_bridge: could not remove %s: %s", name, e)


def install():
    """Called by A0 framework after plugin is placed in usr/plugins/.

    1. Installs system dependencies (x11vnc, novnc).
    2. Ensures the plugin's data directory is gitignored in A0's root.
    3. Cleans up any stale Chromium Singleton files left from a prior run.
    """
    plugin_dir = Path(__file__).resolve().parent

    # --- System dependencies ---
    try:
        result = subprocess.run(
            ["apt-get", "install", "-y", "--no-install-recommends", "x11vnc", "novnc"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            logger.info("phantom_bridge: dependencies installed (x11vnc, novnc)")
        else:
            logger.warning(
                "phantom_bridge: dependency install failed (run execute.py manually): %s",
                result.stderr[:200],
            )
    except Exception as e:
        logger.warning("phantom_bridge: dependency install skipped: %s", e)

    # --- Gitignore safeguard ---
    # Walk up from plugin dir to find A0's root (contains .git/)
    a0_root = plugin_dir
    for _ in range(6):  # usr/plugins/phantom_bridge → 3 levels up max
        a0_root = a0_root.parent
        if (a0_root / ".git").exists():
            break
    else:
        a0_root = None  # type: ignore[assignment]

    if a0_root and (a0_root / ".git").exists():
        try:
            _ensure_gitignore_entry(a0_root)
        except Exception as e:
            logger.warning("phantom_bridge: could not update .gitignore: %s", e)

    # --- Clean up stale Singleton files ---
    _cleanup_singleton_files(plugin_dir)
