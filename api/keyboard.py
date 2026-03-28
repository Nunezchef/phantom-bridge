"""CDP Keyboard Proxy — dispatches keyboard events to the bridge browser."""

import json
import urllib.request
from helpers.api import ApiHandler, Request, Response


# Common key -> windowsVirtualKeyCode mappings
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
    "Space": 32,
}

# Keys that should NOT produce a "char" event
NON_PRINTABLE_KEYS = {
    "Enter", "Backspace", "Tab", "Escape", "Delete",
    "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
    "Home", "End", "PageUp", "PageDown",
    "Shift", "Control", "Alt", "Meta", "CapsLock",
    "F1", "F2", "F3", "F4", "F5", "F6",
    "F7", "F8", "F9", "F10", "F11", "F12",
}


def _virtual_key_code(key: str) -> int:
    """Resolve the windowsVirtualKeyCode for a given key string."""
    if key in KEY_CODES:
        return KEY_CODES[key]
    # For single printable characters, use the uppercase char code
    if len(key) == 1:
        return ord(key.upper())
    return 0


def _resolve_modifiers(modifiers) -> int:
    """Accept modifiers as int bitmask or dict. Returns int bitmask.

    Bitmask: Alt=1, Ctrl=2, Meta=4, Shift=8.
    """
    if isinstance(modifiers, int):
        return modifiers
    if isinstance(modifiers, dict):
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
    return 0


def _is_printable(key: str) -> bool:
    """Return True if the key produces a visible character."""
    return key not in NON_PRINTABLE_KEYS and len(key) == 1


async def _send_key(ws, msg_id: int, key: str, code: str, text: str, modifiers: int) -> int:
    """Send keyDown + optional char + keyUp for one keystroke. Returns next msg_id."""
    vkc = _virtual_key_code(key)
    printable = _is_printable(key)

    # 1. keyDown
    await ws.send(json.dumps({
        "id": msg_id,
        "method": "Input.dispatchKeyEvent",
        "params": {
            "type": "keyDown",
            "key": key,
            "code": code or key,
            "windowsVirtualKeyCode": vkc,
            "nativeVirtualKeyCode": vkc,
            "modifiers": modifiers,
        }
    }))
    await ws.recv()
    msg_id += 1

    # 2. char (only for printable characters)
    if printable:
        char_text = text or key
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Input.dispatchKeyEvent",
            "params": {
                "type": "char",
                "text": char_text,
                "key": key,
                "code": code or key,
                "modifiers": modifiers,
            }
        }))
        await ws.recv()
        msg_id += 1

    # 3. keyUp
    await ws.send(json.dumps({
        "id": msg_id,
        "method": "Input.dispatchKeyEvent",
        "params": {
            "type": "keyUp",
            "key": key,
            "code": code or key,
            "windowsVirtualKeyCode": vkc,
            "nativeVirtualKeyCode": vkc,
            "modifiers": modifiers,
        }
    }))
    await ws.recv()
    msg_id += 1

    return msg_id


def _find_ws_url(page_id: str) -> str | None:
    """Look up the WebSocket debugger URL for a given page_id."""
    with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3) as resp:
        pages = json.loads(resp.read().decode())
    for page in pages:
        if page.get("id") == page_id:
            return page.get("webSocketDebuggerUrl")
    return None


class KeyboardHandler(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        page_id = input.get("page_id", "")
        action = input.get("action", "key")  # "key" | "type_text"

        if not page_id:
            return {"ok": False, "error": "page_id required"}

        try:
            import websockets

            ws_url = _find_ws_url(page_id)
            if not ws_url:
                return {"ok": False, "error": f"Page {page_id} not found"}

            if action == "type_text":
                return await self._type_text(ws_url, input)
            else:
                return await self._single_key(ws_url, input)

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _single_key(self, ws_url: str, input: dict) -> dict:
        """Handle a single keystroke (keyDown + char + keyUp)."""
        import websockets

        key = input.get("key", "")
        code = input.get("code", "")
        text = input.get("text", "")
        modifiers = _resolve_modifiers(input.get("modifiers", 0))

        if not key:
            return {"ok": False, "error": "key required"}

        async with websockets.connect(ws_url) as ws:
            await _send_key(ws, 1, key, code, text, modifiers)

        return {"ok": True, "key": key, "code": code or key}

    async def _type_text(self, ws_url: str, input: dict) -> dict:
        """Type a full string by sending keyDown+char+keyUp for each character."""
        import websockets

        text = input.get("text", "")
        if not text:
            return {"ok": False, "error": "text required for type_text action"}

        modifiers = _resolve_modifiers(input.get("modifiers", 0))
        msg_id = 1

        async with websockets.connect(ws_url) as ws:
            for char in text:
                code = f"Key{char.upper()}" if char.isalpha() else ""
                msg_id = await _send_key(ws, msg_id, char, code, char, modifiers)

        return {"ok": True, "typed": text, "length": len(text)}
