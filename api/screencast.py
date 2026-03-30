"""Screencast API — serves frames and forwards input through A0's port."""

import json
from helpers.api import ApiHandler, Request, Response


class ScreencastHandler(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "frame")

        if action == "frame":
            return self._get_frame()
        elif action == "click":
            return await self._click(input)
        elif action == "key":
            return await self._key(input)
        elif action == "status":
            return self._status()
        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    def _get_frame(self) -> dict | Response:
        """Return the latest screencast frame as base64 JPEG."""
        from usr.plugins.phantom_bridge.screencast import get_screencast_manager

        mgr = get_screencast_manager()
        if not mgr:
            return {"ok": False, "error": "Screencast not running"}

        frame = mgr.get_frame()
        if frame is None:
            return {"ok": False, "error": "No frame available"}

        return {"ok": True, "frame": frame}

    async def _click(self, input: dict) -> dict:
        """Forward a click event."""
        from usr.plugins.phantom_bridge.screencast import get_screencast_manager

        mgr = get_screencast_manager()
        if not mgr:
            return {"ok": False, "error": "Screencast not running"}

        x = input.get("x", 0)
        y = input.get("y", 0)

        # mousePressed + mouseReleased
        await mgr.send_mouse_event("mousePressed", x, y)
        await mgr.send_mouse_event("mouseReleased", x, y)
        return {"ok": True, "clicked": {"x": x, "y": y}}

    async def _key(self, input: dict) -> dict:
        """Forward a key event."""
        from usr.plugins.phantom_bridge.screencast import get_screencast_manager

        mgr = get_screencast_manager()
        if not mgr:
            return {"ok": False, "error": "Screencast not running"}

        key = input.get("key", "")
        code = input.get("code", "")
        text = input.get("text", "")
        modifiers = input.get("modifiers", 0)

        if isinstance(modifiers, dict):
            flags = 0
            if modifiers.get("alt"): flags |= 1
            if modifiers.get("ctrl"): flags |= 2
            if modifiers.get("meta"): flags |= 4
            if modifiers.get("shift"): flags |= 8
            modifiers = flags

        ok = await mgr.send_key_event(key, code, text, modifiers)
        return {"ok": ok}

    def _status(self) -> dict:
        """Check screencast status."""
        from usr.plugins.phantom_bridge.screencast import get_screencast_manager

        mgr = get_screencast_manager()
        return {
            "ok": True,
            "running": mgr is not None and mgr._running,
            "has_frame": mgr is not None and mgr._latest_frame is not None,
        }
