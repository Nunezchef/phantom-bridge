"""CDP Proxy — forwards Chrome DevTools Protocol HTTP endpoints through A0's port.

Proxies /json, /json/version, and screenshot endpoints so users don't need
port 9222 exposed. For WebSocket DevTools connections, serves a landing page
that establishes a WebSocket relay via the browser's own fetch API.
"""

import json
import urllib.request
import base64
from helpers.api import ApiHandler, Request, Response as FlaskResponse

CDP_BASE = "http://127.0.0.1:9222"


class ProxyHandler(ApiHandler):
    """Proxy CDP HTTP endpoints through A0's existing port."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # CDP proxy needs GET without CSRF

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "pages")

        if action == "pages":
            return self._proxy_json()
        elif action == "version":
            return self._proxy_version()
        elif action == "screenshot":
            page_id = input.get("page_id", "")
            return await self._screenshot(page_id)
        elif action == "navigate":
            page_id = input.get("page_id", "")
            url = input.get("url", "")
            return await self._navigate(page_id, url)
        elif action == "reload":
            page_id = input.get("page_id", "")
            return await self._reload(page_id)
        elif action == "go_back":
            page_id = input.get("page_id", "")
            return await self._go_back(page_id)
        elif action == "close_tab":
            page_id = input.get("page_id", "")
            return await self._close_tab(page_id)
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

    async def _screenshot(self, page_id: str) -> dict:
        """Take a screenshot of a page via CDP WebSocket."""
        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            import websockets

            # Get the WebSocket URL for this page
            with urllib.request.urlopen(f"{CDP_BASE}/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())

            ws_url = None
            for page in pages:
                if page.get("id") == page_id:
                    ws_url = page.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            # Connect and take screenshot
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.captureScreenshot",
                    "params": {"format": "jpeg", "quality": 70}
                }))
                result = json.loads(await ws.recv())
                if "result" in result and "data" in result["result"]:
                    return {
                        "ok": True,
                        "screenshot": result["result"]["data"],  # base64 JPEG
                        "format": "jpeg",
                    }
                return {"ok": False, "error": "Screenshot failed"}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _navigate(self, page_id: str, url: str) -> dict:
        """Navigate a page to a URL via CDP."""
        if not page_id or not url:
            return {"ok": False, "error": "page_id and url required"}

        try:
            import websockets

            with urllib.request.urlopen(f"{CDP_BASE}/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())

            ws_url = None
            for page in pages:
                if page.get("id") == page_id:
                    ws_url = page.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {"url": url}
                }))
                result = json.loads(await ws.recv())
                return {"ok": True, "result": result.get("result", {})}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _reload(self, page_id: str) -> dict:
        """Reload the current page via CDP."""
        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            import websockets

            with urllib.request.urlopen(f"{CDP_BASE}/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())

            ws_url = None
            for page in pages:
                if page.get("id") == page_id:
                    ws_url = page.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.reload",
                }))
                await ws.recv()
                return {"ok": True}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _go_back(self, page_id: str) -> dict:
        """Navigate back in history via CDP."""
        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            import websockets

            with urllib.request.urlopen(f"{CDP_BASE}/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())

            ws_url = None
            for page in pages:
                if page.get("id") == page_id:
                    ws_url = page.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            async with websockets.connect(ws_url) as ws:
                # Get navigation history
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.getNavigationHistory",
                }))
                result = json.loads(await ws.recv())
                history = result.get("result", {})
                current_index = history.get("currentIndex", 0)

                if current_index <= 0:
                    return {"ok": True, "message": "Already at first page"}

                # Navigate to previous entry
                entries = history.get("entries", [])
                prev_entry = entries[current_index - 1]
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Page.navigateToHistoryEntry",
                    "params": {"entryId": prev_entry["id"]}
                }))
                await ws.recv()
                return {"ok": True}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _close_tab(self, page_id: str) -> dict:
        """Close a browser tab via CDP."""
        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            url = f"{CDP_BASE}/json/close/{page_id}"
            with urllib.request.urlopen(url, timeout=3) as resp:
                return {"ok": True, "closed": page_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
