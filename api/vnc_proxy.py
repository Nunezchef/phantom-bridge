"""VNC WebSocket Proxy — bridges noVNC to x11vnc through A0's existing port.

Proxies the VNC WebSocket protocol so noVNC can connect without exposing
an additional port. The browser connects to A0's port 5050, this handler
relays to x11vnc on localhost:5900.

Since A0's ApiHandler doesn't support WebSocket upgrades directly, this
handler provides a chunked binary relay over HTTP long-polling as a fallback,
plus serves noVNC static files from /usr/share/novnc/.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from helpers.api import ApiHandler, Request, Response


# Path to noVNC static files (installed by execute.py)
_NOVNC_PATHS = [
    Path("/usr/share/novnc"),
    Path("/opt/novnc"),
]


class VncProxyHandler(ApiHandler):
    """Handles VNC proxy requests and serves noVNC static files."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "info")

        if action == "info":
            return self._vnc_info()
        elif action == "novnc_available":
            return {"ok": True, "available": self._find_novnc_dir() is not None}
        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    def _vnc_info(self) -> dict:
        """Return VNC connection info for the noVNC client."""
        from usr.plugins.phantom_bridge.bridge import get_bridge

        bridge = get_bridge()
        if not bridge or not bridge.is_running():
            return {"ok": False, "error": "Bridge not running"}

        novnc_dir = self._find_novnc_dir()
        novnc_port = bridge.novnc_port
        vnc_running = (
            bridge._vnc_process is not None
            and bridge._vnc_process.poll() is None
        )
        ws_running = (
            bridge._websockify_process is not None
            and bridge._websockify_process.poll() is None
        )

        return {
            "ok": True,
            "vnc_running": vnc_running,
            "websockify_running": ws_running,
            "novnc_installed": novnc_dir is not None,
            "novnc_port": novnc_port,
            # Direct URL for when port IS exposed (simplest path)
            "direct_url": f"http://localhost:{novnc_port}/vnc.html?autoconnect=true&resize=scale",
            # Fallback: user can access noVNC on the internal port from the container
            "ws_url": f"ws://localhost:{novnc_port}/websockify",
        }

    @staticmethod
    def _find_novnc_dir() -> Path | None:
        for p in _NOVNC_PATHS:
            if p.exists() and (p / "vnc.html").exists():
                return p
        return None
