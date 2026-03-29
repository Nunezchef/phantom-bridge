"""
Screencast Manager — streams browser frames via CDP Page.startScreencast.

Maintains a persistent CDP WebSocket connection, receives frames as Chrome
pushes them (event-driven, not polling), and buffers the latest frame for
instant retrieval by the API handler. Also forwards input events (mouse,
keyboard) through the same persistent connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger("phantom_bridge")

_manager: ScreencastManager | None = None


def get_screencast_manager() -> ScreencastManager | None:
    return _manager


class ScreencastManager:
    """Manages CDP screencast streaming and input forwarding."""

    def __init__(self, port: int = 9222):
        global _manager
        self._port = port
        self._ws: ClientConnection | None = None
        self._msg_id = 0
        self._latest_frame: str | None = None  # base64 JPEG
        self._frame_metadata: dict = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._connected = False
        _manager = self

    async def start(self) -> None:
        """Connect to Chrome and start screencast."""
        if self._running:
            return

        ws_url = await self._discover_ws_url()
        if not ws_url:
            logger.warning("screencast: no page target found")
            return

        try:
            self._ws = await websockets.connect(
                ws_url,
                max_size=16 * 1024 * 1024,
                close_timeout=5,
            )
            self._connected = True
            self._running = True

            # Enable Page domain
            await self._send("Page.enable")

            # Start screencast — Chrome pushes frames when screen changes
            await self._send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 60,
                "maxWidth": 1280,
                "maxHeight": 900,
                "everyNthFrame": 1,
            })

            # Start background listener
            self._task = asyncio.create_task(self._listen())
            logger.info("screencast: started streaming")

        except Exception as e:
            logger.warning("screencast: failed to start: %s", e)
            self._running = False

    async def stop(self) -> None:
        """Stop screencast and disconnect."""
        global _manager
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._ws and self._connected:
            try:
                await self._send("Page.stopScreencast")
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass

        self._ws = None
        self._connected = False
        self._latest_frame = None
        _manager = None
        logger.info("screencast: stopped")

    def get_frame(self) -> str | None:
        """Return the latest frame as base64 JPEG, or None."""
        return self._latest_frame

    async def send_mouse_event(
        self, event_type: str, x: int, y: int, button: str = "left", click_count: int = 1
    ) -> bool:
        """Send a mouse event via CDP."""
        if not self._connected or not self._ws:
            return False

        try:
            # JS-level click for better reliability (iframes, captchas)
            if event_type == "mousePressed":
                await self._send("Runtime.evaluate", {
                    "expression": (
                        f"(function(){{"
                        f"var el=document.elementFromPoint({x},{y});"
                        f"if(el){{el.focus();el.click();}}"
                        f"}})()"
                    )
                })

            # Also send raw CDP events
            await self._send("Input.dispatchMouseEvent", {
                "type": event_type,
                "x": x, "y": y,
                "button": button,
                "clickCount": click_count,
            })
            return True
        except Exception as e:
            logger.debug("screencast: mouse event failed: %s", e)
            return False

    async def send_key_event(
        self, key: str, code: str = "", text: str = "", modifiers: int = 0
    ) -> bool:
        """Send a key event (keyDown + char + keyUp) via CDP."""
        if not self._connected or not self._ws:
            return False

        try:
            vkc = ord(key.upper()) if len(key) == 1 else 0
            is_printable = len(key) == 1

            # keyDown
            await self._send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": key,
                "code": code or key,
                "windowsVirtualKeyCode": vkc,
                "modifiers": modifiers,
            })

            # char (printable only)
            if is_printable:
                await self._send("Input.dispatchKeyEvent", {
                    "type": "char",
                    "text": text or key,
                    "key": key,
                    "code": code or key,
                    "modifiers": modifiers,
                })

            # keyUp
            await self._send("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": key,
                "code": code or key,
                "windowsVirtualKeyCode": vkc,
                "modifiers": modifiers,
            })
            return True
        except Exception as e:
            logger.debug("screencast: key event failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _send(self, method: str, params: dict | None = None) -> dict:
        """Send a CDP command and wait for the matching response."""
        if not self._ws:
            raise RuntimeError("Not connected")

        self._msg_id += 1
        msg: dict[str, Any] = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        await self._ws.send(json.dumps(msg))

        # We don't wait for response here — the listener handles it
        # For fire-and-forget commands this is fine
        return {}

    async def _listen(self) -> None:
        """Background listener — receives frames and command responses."""
        if not self._ws:
            return

        try:
            async for raw in self._ws:
                if not self._running:
                    break

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                method = msg.get("method", "")

                # Handle screencast frame
                if method == "Page.screencastFrame":
                    params = msg.get("params", {})
                    self._latest_frame = params.get("data")
                    self._frame_metadata = params.get("metadata", {})

                    # Acknowledge frame so Chrome sends the next one
                    session_id = params.get("sessionId")
                    if session_id is not None:
                        try:
                            await self._ws.send(json.dumps({
                                "id": self._msg_id + 1000,
                                "method": "Page.screencastFrameAck",
                                "params": {"sessionId": session_id}
                            }))
                        except Exception:
                            pass

        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            logger.info("screencast: WebSocket connection closed")
        except Exception as e:
            logger.warning("screencast: listener error: %s", e)
        finally:
            self._connected = False

    async def _discover_ws_url(self) -> str | None:
        """Find the first page target's WebSocket URL."""
        for attempt in range(5):
            try:
                url = f"http://127.0.0.1:{self._port}/json"
                with urllib.request.urlopen(url, timeout=2) as resp:
                    targets = json.loads(resp.read().decode())
                for target in targets:
                    if target.get("type") == "page":
                        return target.get("webSocketDebuggerUrl")
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return None
