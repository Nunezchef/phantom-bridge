"""
CDP WebSocket Client — shared base for all observer layers.

Connects to Chrome's DevTools Protocol via WebSocket, sends commands,
and dispatches events to registered subscribers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.request
from collections import defaultdict
from typing import Any, Callable

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger("phantom_bridge")

# Retry configuration for initial connection
_MAX_CONNECT_ATTEMPTS = 10
_INITIAL_BACKOFF = 0.5  # seconds
_MAX_BACKOFF = 5.0
_HEARTBEAT_INTERVAL = 15  # seconds between heartbeat checks


class CDPClient:
    """Chrome DevTools Protocol WebSocket client."""

    def __init__(self, port: int = 9222):
        self._port = port
        self._ws: ClientConnection | None = None
        self._msg_id = 0
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._connected = False
        self._ws_url: str | None = None
        self._listen_task: asyncio.Task | None = None
        self._shutdown = False
        self._healthy = False
        self._last_heartbeat: float = 0.0
        self._heartbeat_task: asyncio.Task | None = None
        self._on_health_change: Callable[[bool], Any] | None = None
        self._healthy = False
        self._last_heartbeat: float = 0.0
        self._heartbeat_task: asyncio.Task | None = None
        self._on_health_change: Callable[[bool], Any] | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to Chrome's CDP WebSocket endpoint.

        1. GET http://127.0.0.1:{port}/json to list debuggable pages
        2. Pick the first 'page' type target
        3. Connect to its webSocketDebuggerUrl
        """
        self._shutdown = False
        self._ws_url = await self._discover_ws_url()
        await self._connect_ws()
        self._healthy = True
        self._last_heartbeat = time.monotonic()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._healthy = True
        self._last_heartbeat = time.monotonic()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _discover_ws_url(self) -> str:
        """Discover the WebSocket URL with retry + backoff."""
        backoff = _INITIAL_BACKOFF
        last_error: Exception | None = None

        for attempt in range(1, _MAX_CONNECT_ATTEMPTS + 1):
            try:
                url = f"http://127.0.0.1:{self._port}/json"
                with urllib.request.urlopen(url, timeout=2) as resp:
                    targets = json.loads(resp.read().decode())

                for target in targets:
                    if target.get("type") == "page":
                        ws_url = target.get("webSocketDebuggerUrl")
                        if ws_url:
                            logger.info(
                                "cdp_client: found page target on attempt %d: %s",
                                attempt,
                                target.get("url", ""),
                            )
                            return ws_url

                raise RuntimeError("No debuggable page targets found")

            except Exception as exc:
                last_error = exc
                if attempt < _MAX_CONNECT_ATTEMPTS:
                    logger.debug(
                        "cdp_client: connect attempt %d/%d failed: %s (retry in %.1fs)",
                        attempt,
                        _MAX_CONNECT_ATTEMPTS,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF)

        raise RuntimeError(
            f"Failed to discover CDP WebSocket after {_MAX_CONNECT_ATTEMPTS} "
            f"attempts: {last_error}"
        )

    async def _connect_ws(self) -> None:
        """Establish the WebSocket connection."""
        if not self._ws_url:
            raise RuntimeError("No WebSocket URL discovered")

        self._ws = await websockets.connect(
            self._ws_url,
            max_size=16 * 1024 * 1024,  # 16 MB for large payloads
            close_timeout=5,
        )
        self._connected = True
        logger.info("cdp_client: WebSocket connected to %s", self._ws_url)

    async def disconnect(self) -> None:
        """Clean disconnect."""
        self._shutdown = True
        self._connected = False
        self._healthy = False

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        # Fail any pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(RuntimeError("CDP client disconnected"))
        self._pending.clear()

        logger.info("cdp_client: disconnected")

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def set_health_callback(self, callback: Callable[[bool], Any]) -> None:
        """Register a callback invoked when CDP health status changes."""
        self._on_health_change = callback

    async def _heartbeat_loop(self) -> None:
        """Periodically verify CDP is responsive via Browser.getVersion."""
        while not self._shutdown:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            if self._shutdown or not self._connected:
                continue
            try:
                await self.send("Browser.getVersion")
                prev = self._healthy
                self._healthy = True
                self._last_heartbeat = time.monotonic()
                if not prev and self._on_health_change:
                    self._on_health_change(True)
            except Exception as exc:
                if self._healthy and self._on_health_change:
                    self._on_health_change(False)
                self._healthy = False
                logger.warning("cdp_client: heartbeat failed: %s", exc)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def send(self, method: str, params: dict | None = None) -> dict:
        """Send a CDP command and wait for the response.

        Uses incrementing message IDs. Returns the 'result' dict.
        """
        if not self._ws or not self._connected:
            raise RuntimeError("CDP client is not connected")

        self._msg_id += 1
        msg_id = self._msg_id

        message: dict[str, Any] = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        fut: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut

        try:
            await self._ws.send(json.dumps(message))
        except Exception:
            self._pending.pop(msg_id, None)
            raise

        try:
            return await asyncio.wait_for(fut, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise RuntimeError(f"CDP command {method} timed out after 30s")

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def subscribe(self, event: str, callback: Callable) -> None:
        """Register a callback for a CDP event (e.g., 'Page.loadEventFired').

        The callback receives the event params dict. Async callbacks are
        awaited; sync callbacks are called directly.
        """
        self._subscribers[event].append(callback)

    async def enable_domains(self, *domains: str) -> None:
        """Enable CDP domains (Page, Network, Runtime, etc.).

        Calls {domain}.enable for each.
        """
        for domain in domains:
            await self.send(f"{domain}.enable")
            logger.debug("cdp_client: enabled domain %s", domain)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    async def get_cookies(self) -> list[dict]:
        """Get all cookies via Network.getAllCookies."""
        result = await self.send("Network.getAllCookies")
        return result.get("cookies", [])

    # ------------------------------------------------------------------
    # Background listener
    # ------------------------------------------------------------------

    async def _listen(self) -> None:
        """Background listener that dispatches events to subscribers.

        Handles reconnection on WebSocket drop and JSON parse errors.
        """
        while not self._shutdown:
            try:
                await self._receive_loop()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._shutdown:
                    break
                logger.warning("cdp_client: WebSocket dropped: %s", exc)
                self._connected = False
                # Attempt reconnect
                await self._reconnect()

    async def _receive_loop(self) -> None:
        """Read messages from the WebSocket and dispatch them."""
        if not self._ws:
            raise RuntimeError("No WebSocket connection")

        async for raw in self._ws:
            if self._shutdown:
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("cdp_client: failed to parse message: %s", raw[:200])
                continue

            # Response to a command we sent
            if "id" in msg:
                msg_id = msg["id"]
                fut = self._pending.pop(msg_id, None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(
                            RuntimeError(
                                f"CDP error: {msg['error'].get('message', msg['error'])}"
                            )
                        )
                    else:
                        fut.set_result(msg.get("result", {}))

            # Event notification
            if "method" in msg:
                event_name = msg["method"]
                params = msg.get("params", {})
                for callback in self._subscribers.get(event_name, []):
                    try:
                        result = callback(params)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception(
                            "cdp_client: error in subscriber for %s", event_name
                        )

    async def _reconnect(self) -> None:
        """Attempt to reconnect to the WebSocket with backoff."""
        backoff = _INITIAL_BACKOFF
        for attempt in range(1, _MAX_CONNECT_ATTEMPTS + 1):
            if self._shutdown:
                return
            try:
                logger.info(
                    "cdp_client: reconnect attempt %d/%d",
                    attempt,
                    _MAX_CONNECT_ATTEMPTS,
                )
                # Re-discover in case the target changed
                self._ws_url = await self._discover_ws_url()
                await self._connect_ws()
                self._healthy = True
                self._last_heartbeat = time.monotonic()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                if self._on_health_change:
                    self._on_health_change(True)
                logger.info("cdp_client: reconnected successfully")
                return
            except Exception as exc:
                logger.debug("cdp_client: reconnect failed: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

        logger.error(
            "cdp_client: failed to reconnect after %d attempts", _MAX_CONNECT_ATTEMPTS
        )
        self._connected = False
        self._healthy = False
        if self._on_health_change:
            self._on_health_change(False)
        self._healthy = False
        if self._on_health_change:
            self._on_health_change(False)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the WebSocket is currently connected."""
        return self._connected

    @property
    def healthy(self) -> bool:
        """Whether CDP is responsive (last heartbeat succeeded)."""
        return self._healthy and self._connected

    @property
    def last_heartbeat(self) -> float:
        """Monotonic timestamp of last successful heartbeat."""
        return self._last_heartbeat

    @property
    def healthy(self) -> bool:
        """Whether CDP is responsive (last heartbeat succeeded)."""
        return self._healthy and self._connected

    @property
    def last_heartbeat(self) -> float:
        """Monotonic timestamp of last successful heartbeat."""
        return self._last_heartbeat
