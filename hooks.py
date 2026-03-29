"""Phantom Bridge — Framework lifecycle hooks."""

import subprocess
import logging

logger = logging.getLogger("phantom_bridge")


def install():
    """Called by A0 framework after plugin is placed in usr/plugins/.
    Installs x11vnc and novnc dependencies."""
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
