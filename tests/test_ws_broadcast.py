"""Tests for ws_broadcast.py — envelope helper and socketio integration."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to create a fake run_ui module
# ---------------------------------------------------------------------------

def _make_fake_run_ui(sio=None):
    """Return a minimal fake run_ui module with socketio_server set."""
    mod = ModuleType("run_ui")
    mod.socketio_server = sio
    return mod


# ---------------------------------------------------------------------------
# _make_envelope
# ---------------------------------------------------------------------------

class TestMakeEnvelope:
    def test_contains_required_fields(self):
        from ws_broadcast import _make_envelope
        env = _make_envelope({"key": "value"})
        assert env["handlerId"] == "phantom_bridge"
        assert "eventId" in env
        assert "correlationId" in env
        assert "ts" in env
        assert env["data"] == {"key": "value"}

    def test_event_id_and_correlation_id_are_uuids(self):
        from ws_broadcast import _make_envelope
        import re
        uuid_re = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.I,
        )
        env = _make_envelope({})
        assert uuid_re.match(env["eventId"]), f"bad eventId: {env['eventId']}"
        assert uuid_re.match(env["correlationId"]), f"bad correlationId: {env['correlationId']}"

    def test_event_id_and_correlation_id_differ(self):
        from ws_broadcast import _make_envelope
        env = _make_envelope({})
        assert env["eventId"] != env["correlationId"]

    def test_timestamp_is_valid_iso_with_z(self):
        from ws_broadcast import _make_envelope
        env = _make_envelope({})
        ts = env["ts"]
        assert ts.endswith("Z"), f"timestamp should end with Z: {ts}"
        # Should parse without error
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")

    def test_timestamp_millisecond_precision(self):
        """ts should have exactly 3 fractional digits (milliseconds)."""
        from ws_broadcast import _make_envelope
        env = _make_envelope({})
        # e.g. "2025-01-15T12:34:56.789Z"
        ts = env["ts"]
        dot_index = ts.index(".")
        frac = ts[dot_index + 1 : ts.index("Z")]
        assert len(frac) == 3, f"expected 3 fractional digits, got: {frac!r}"

    def test_each_call_produces_unique_ids(self):
        from ws_broadcast import _make_envelope
        env1 = _make_envelope({})
        env2 = _make_envelope({})
        assert env1["eventId"] != env2["eventId"]
        assert env1["correlationId"] != env2["correlationId"]

    def test_data_is_passed_through(self):
        from ws_broadcast import _make_envelope
        payload = {"foo": 1, "bar": [1, 2, 3]}
        env = _make_envelope(payload)
        assert env["data"] == payload


# ---------------------------------------------------------------------------
# _get_socketio
# ---------------------------------------------------------------------------

class TestGetSocketio:
    def test_returns_none_when_run_ui_not_importable(self):
        from ws_broadcast import _get_socketio
        with patch.dict(sys.modules, {"run_ui": None}):
            result = _get_socketio()
        assert result is None

    def test_returns_socketio_server_attribute(self):
        from ws_broadcast import _get_socketio
        mock_sio = MagicMock()
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            result = _get_socketio()
        assert result is mock_sio

    def test_returns_none_when_attribute_missing(self):
        from ws_broadcast import _get_socketio
        fake_mod = ModuleType("run_ui")  # no socketio_server attribute
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            result = _get_socketio()
        assert result is None


# ---------------------------------------------------------------------------
# broadcast()
# ---------------------------------------------------------------------------

class TestBroadcast:
    @pytest.mark.asyncio
    async def test_emits_to_root_namespace(self):
        from ws_broadcast import broadcast
        mock_sio = AsyncMock()
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            await broadcast("phantom_bridge_status", {"running": True})

        mock_sio.emit.assert_awaited_once()
        call_args = mock_sio.emit.call_args
        assert call_args.args[0] == "phantom_bridge_status"
        assert call_args.kwargs.get("namespace") == "/"

    @pytest.mark.asyncio
    async def test_emits_valid_envelope(self):
        from ws_broadcast import broadcast
        mock_sio = AsyncMock()
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            await broadcast("phantom_bridge_auth", {"domain": "example.com"})

        envelope = mock_sio.emit.call_args.args[1]
        assert envelope["handlerId"] == "phantom_bridge"
        assert "eventId" in envelope
        assert "correlationId" in envelope
        assert "ts" in envelope
        assert envelope["data"] == {"domain": "example.com"}

    @pytest.mark.asyncio
    async def test_does_nothing_when_run_ui_unavailable(self):
        from ws_broadcast import broadcast
        with patch.dict(sys.modules, {"run_ui": None}):
            # Should not raise
            await broadcast("phantom_bridge_status", {"running": False})

    @pytest.mark.asyncio
    async def test_does_nothing_when_socketio_is_none(self):
        from ws_broadcast import broadcast
        fake_mod = _make_fake_run_ui(sio=None)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            # Should not raise
            await broadcast("phantom_bridge_status", {"running": False})

    @pytest.mark.asyncio
    async def test_does_not_raise_when_emit_fails(self):
        from ws_broadcast import broadcast
        mock_sio = AsyncMock()
        mock_sio.emit.side_effect = RuntimeError("connection lost")
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            # Should swallow the error
            await broadcast("phantom_bridge_status", {"running": True})

    @pytest.mark.asyncio
    async def test_event_type_forwarded_correctly(self):
        from ws_broadcast import broadcast
        mock_sio = AsyncMock()
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            await broadcast("phantom_bridge_auth", {})

        assert mock_sio.emit.call_args.args[0] == "phantom_bridge_auth"

    @pytest.mark.asyncio
    async def test_empty_data_produces_valid_envelope(self):
        from ws_broadcast import broadcast
        mock_sio = AsyncMock()
        fake_mod = _make_fake_run_ui(sio=mock_sio)
        with patch.dict(sys.modules, {"run_ui": fake_mod}):
            await broadcast("phantom_bridge_status", {})

        envelope = mock_sio.emit.call_args.args[1]
        assert envelope["data"] == {}
