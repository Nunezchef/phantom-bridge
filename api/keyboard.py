"""CDP Keyboard Proxy — dispatches keyboard events to the bridge browser."""

import json
import urllib.request
from helpers.api import ApiHandler, Request, Response


# Common key → windowsVirtualKeyCode mappings
KEY_CODES = {
    "Enter": 13,
    "Backspace": 8,
    "Tab": 9,
    "Escape": 27,
    "Delete": 46,
    "ArrowUp": 38,
    "ArrowDown": 40,
    "ArrowLeft": 37,
    "ArrowRight": 39,
    "Home": 36,
    "End": 35,
    "PageUp": 33,
    "PageDown": 34,
    "Shift": 16,
    "Control": 17,
    "Alt": 18,
    "Meta": 91,
    "CapsLock": 20,
    "Space": 32,
    " ": 32,
    "F1": 112, "F2": 113, "F3": 114, "F4": 115,
    "F5": 116, "F6": 117, "F7": 118, "F8": 119,
    "F9": 120, "F10": 121, "F11": 122, "F12": 123,
}


def _virtual_key_code(key: str) -> int:
    """Resolve the windowsVirtualKeyCode for a given key string."""
    if key in KEY_CODES:
        return KEY_CODES[key]
    # For single printable characters, use the uppercase char code
    if len(key) == 1:
        return ord(key.upper())
    return 0


def _modifier_flags(modifiers: dict) -> int:
    """Build CDP modifier bitmask from a modifiers dict."""
    flags = 0
    if modifiers.get("alt"):
        flags |= 1
    if modifiers.get("ctrl"):
        flags |= 2
    if modifiers.get("meta"):
        flags |= 4
    if modifiers.get("shift"):
        flags |= 8
    return flags


class KeyboardHandler(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        page_id = input.get("page_id", "")
        key = input.get("key", "")
        code = input.get("code", "")
        text = input.get("text", "")
        modifiers = input.get("modifiers", {})
        event_type = input.get("type", "full")  # "full" | "keyDown" | "keyUp" | "char"

        if not page_id:
            return {"ok": False, "error": "page_id required"}
        if not key:
            return {"ok": False, "error": "key required"}

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

            vkc = _virtual_key_code(key)
            mod_flags = _modifier_flags(modifiers)
            msg_id = 1

            # Determine if this is a printable character (needs char event)
            is_printable = len(key) == 1 and not modifiers.get("ctrl") and not modifiers.get("meta")

            async with websockets.connect(ws_url) as ws:
                if event_type in ("full", "keyDown"):
                    # keyDown
                    await ws.send(json.dumps({
                        "id": msg_id,
                        "method": "Input.dispatchKeyEvent",
                        "params": {
                            "type": "keyDown",
                            "key": key,
                            "code": code or key,
                            "windowsVirtualKeyCode": vkc,
                            "nativeVirtualKeyCode": vkc,
                            "modifiers": mod_flags,
                        }
                    }))
                    await ws.recv()
                    msg_id += 1

                if event_type in ("full", "char"):
                    # char event (only for printable characters)
                    char_text = text or (key if is_printable else "")
                    if char_text:
                        await ws.send(json.dumps({
                            "id": msg_id,
                            "method": "Input.dispatchKeyEvent",
                            "params": {
                                "type": "char",
                                "text": char_text,
                                "key": key,
                                "code": code or key,
                                "modifiers": mod_flags,
                            }
                        }))
                        await ws.recv()
                        msg_id += 1

                if event_type in ("full", "keyUp"):
                    # keyUp
                    await ws.send(json.dumps({
                        "id": msg_id,
                        "method": "Input.dispatchKeyEvent",
                        "params": {
                            "type": "keyUp",
                            "key": key,
                            "code": code or key,
                            "windowsVirtualKeyCode": vkc,
                            "nativeVirtualKeyCode": vkc,
                            "modifiers": mod_flags,
                        }
                    }))
                    await ws.recv()

            return {"ok": True, "key": key, "code": code or key}

        except Exception as e:
            return {"ok": False, "error": str(e)}
