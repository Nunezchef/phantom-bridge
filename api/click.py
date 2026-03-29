"""CDP Click Proxy — dispatches mouse events to the bridge browser.

Uses a two-phase approach:
1. Try Runtime.evaluate with elementFromPoint + click() — works for
   most elements including those inside iframes and shadow DOM.
2. Fall back to Input.dispatchMouseEvent for raw coordinate clicks.
"""

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
                # Phase 1: Try JS-level click via elementFromPoint
                # This reaches elements in iframes, shadow DOM, and handles
                # event listeners that raw Input events may miss (e.g. captchas).
                js_click = (
                    f"(function() {{"
                    f"  var el = document.elementFromPoint({x}, {y});"
                    f"  if (!el) return 'no_element';"
                    f"  el.focus();"
                    f"  el.click();"
                    f"  return 'clicked:' + el.tagName + '.' + (el.className || '').toString().slice(0,50);"
                    f"}})()"
                )
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {"expression": js_click}
                }))
                js_result = json.loads(await ws.recv())
                js_value = js_result.get("result", {}).get("result", {}).get("value", "")

                # Phase 2: Also dispatch raw mouse events for elements that
                # rely on mousedown/mouseup (drag handles, canvas, etc.)
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Input.dispatchMouseEvent",
                    "params": {
                        "type": "mousePressed",
                        "x": x, "y": y,
                        "button": "left",
                        "clickCount": 1,
                    }
                }))
                await ws.recv()

                await ws.send(json.dumps({
                    "id": 3,
                    "method": "Input.dispatchMouseEvent",
                    "params": {
                        "type": "mouseReleased",
                        "x": x, "y": y,
                        "button": "left",
                        "clickCount": 1,
                    }
                }))
                await ws.recv()

            return {"ok": True, "clicked": {"x": x, "y": y}, "js_click": js_value}

        except Exception as e:
            return {"ok": False, "error": str(e)}
