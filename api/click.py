"""CDP Click Proxy — dispatches mouse events to the bridge browser."""

import json
import urllib.request
from helpers.api import ApiHandler, Request, Response


class ClickHandler(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        page_id = input.get("page_id", "")
        x = input.get("x", 0)
        y = input.get("y", 0)

        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            import websockets

            # Find page WebSocket URL
            with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3) as resp:
                pages = json.loads(resp.read().decode())

            ws_url = None
            for page in pages:
                if page.get("id") == page_id:
                    ws_url = page.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            async with websockets.connect(ws_url) as ws:
                # Mouse pressed
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Input.dispatchMouseEvent",
                    "params": {
                        "type": "mousePressed",
                        "x": x, "y": y,
                        "button": "left",
                        "clickCount": 1,
                    }
                }))
                await ws.recv()

                # Mouse released
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Input.dispatchMouseEvent",
                    "params": {
                        "type": "mouseReleased",
                        "x": x, "y": y,
                        "button": "left",
                        "clickCount": 1,
                    }
                }))
                await ws.recv()

            return {"ok": True, "clicked": {"x": x, "y": y}}

        except Exception as e:
            return {"ok": False, "error": str(e)}
