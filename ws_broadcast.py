"""
WebSocket broadcast helper for Phantom Bridge.

Emits properly-enveloped Socket.IO events to all connected A0 clients so the
frontend can react to bridge events in real time instead of polling.

A0 v1.5's WebSocket client (websocket.js) validates every incoming message
against the ServerDeliveryEnvelope schema:
    { handlerId, eventId, correlationId, ts, data }

We produce that envelope here so frontend subscribers get clean objects.

Falls back silently when A0's socketio_server isn't accessible (unit tests,
standalone execution, or older A0 versions without the WS system).

Event types emitted:
    phantom_bridge_status  — bridge started or stopped
    phantom_bridge_auth    — a new domain authenticated its session
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("phantom_bridge")

# Stable handler identifier used in every envelope we emit.
_HANDLER_ID = "phantom_bridge"


def _make_envelope(data: dict[str, Any]) -> dict[str, Any]:
    """Wrap *data* in the A0 ServerDeliveryEnvelope format.

    The frontend's validateServerEnvelope() requires all four metadata fields
    (handlerId, eventId, correlationId, ts) to be non-empty strings, and data
    to be a plain object.
    """
    now = datetime.now(timezone.utc)
    # A0 expects millisecond precision with a trailing Z  e.g. "2025-01-15T12:34:56.789Z"
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return {
        "handlerId": _HANDLER_ID,
        "eventId": str(uuid.uuid4()),
        "correlationId": str(uuid.uuid4()),
        "ts": ts,
        "data": data,
    }


def _get_socketio():
    """Return A0's socketio.AsyncServer, or None if not reachable."""
    try:
        import run_ui  # A0 module — only present when running inside A0
        sio = getattr(run_ui, "socketio_server", None)
        return sio
    except ImportError:
        return None
    except Exception:
        return None


async def broadcast(event_type: str, data: dict[str, Any]) -> None:
    """Emit *event_type* to all connected clients in the root namespace.

    Wraps *data* in A0's ServerDeliveryEnvelope before emitting so the
    frontend's websocket.on() subscriber receives a validated envelope object.

    Does nothing (and does not raise) if the socketio server is unavailable.

    Args:
        event_type: Socket.IO event name, e.g. ``"phantom_bridge_status"``.
        data:       Payload dict placed in the ``data`` field of the envelope.
    """
    sio = _get_socketio()
    if sio is None:
        return

    envelope = _make_envelope(data)
    try:
        await sio.emit(event_type, envelope, namespace="/")
        logger.debug("ws_broadcast: emitted %s → %s", event_type, data)
    except Exception as exc:
        # Non-fatal — WS infrastructure may not be fully initialised yet.
        logger.debug("ws_broadcast: emit failed (%s): %s", event_type, exc)
