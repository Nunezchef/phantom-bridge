"""CDP Proxy — exposes Chrome DevTools Protocol page list through A0's port."""

import json
import urllib.request
from helpers.api import ApiHandler, Request, Response as FlaskResponse

CDP_BASE = "http://127.0.0.1:9222"


class ProxyHandler(ApiHandler):
    """Proxy CDP HTTP endpoints through A0's existing port."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "pages")

        if action == "pages":
            return self._proxy_json()
        elif action == "version":
            return self._proxy_version()
        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    def _proxy_json(self) -> dict:
        """List inspectable pages."""
        try:
            with urllib.request.urlopen(f"{CDP_BASE}/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())
                return {"ok": True, "pages": pages}
        except Exception as e:
            return {"ok": True, "pages": [], "bridge_running": False, "error": str(e)}

    def _proxy_version(self) -> dict:
        """Get Chrome version info."""
        try:
            with urllib.request.urlopen(f"{CDP_BASE}/json/version", timeout=3) as resp:
                version = json.loads(resp.read().decode())
                return {"ok": True, "version": version}
        except Exception as e:
            return {"ok": False, "error": str(e)}
