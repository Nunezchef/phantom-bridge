"""Tests for the auth callback chain:
  AuthRegistry.set_auth_callback  →  ObserverManager._on_auth_detected  →  ws_broadcast
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so we can import observer modules without a real CDP connection
# ---------------------------------------------------------------------------

class _FakeCDPClient:
    async def connect(self): pass
    async def disconnect(self): pass
    async def subscribe(self, event, cb): pass
    async def enable_domains(self, *domains): pass
    async def get_cookies(self): return []
    async def send(self, method, params=None): return {}
    async def _listen(self): await asyncio.sleep(9999)


# ---------------------------------------------------------------------------
# AuthRegistry — set_auth_callback / fire on detection
# ---------------------------------------------------------------------------

class TestAuthRegistryCallback:
    def _make_registry(self, tmp_path: Path):
        from observer.auth_registry import AuthRegistry
        return AuthRegistry(cdp=_FakeCDPClient(), data_dir=tmp_path)

    def test_callback_is_none_by_default(self, tmp_path):
        reg = self._make_registry(tmp_path)
        assert reg._auth_callback is None

    def test_set_auth_callback_stores_callable(self, tmp_path):
        reg = self._make_registry(tmp_path)
        cb = AsyncMock()
        reg.set_auth_callback(cb)
        assert reg._auth_callback is cb

    @pytest.mark.asyncio
    async def test_callback_fired_after_auth_detected(self, tmp_path):
        from observer.auth_registry import AuthRegistry, AuthEntry

        reg = AuthRegistry(cdp=_FakeCDPClient(), data_dir=tmp_path)
        fired: list[tuple] = []

        async def on_auth(domain, entry):
            fired.append((domain, entry))

        reg.set_auth_callback(on_auth)

        # Inject a cookie that looks like an auth session cookie
        cookies = [
            {
                "name": "session",
                "domain": "example.com",
                "httpOnly": True,
                "secure": True,
                "expires": -1,
                "value": "abc123",
                "path": "/",
            }
        ]
        await reg._detect_auth_cookies("example.com", cookies)
        # create_task schedules the callback — give it a tick to run
        await asyncio.sleep(0)

        assert len(fired) == 1
        domain, entry = fired[0]
        assert domain == "example.com"
        assert entry.authenticated is True

    @pytest.mark.asyncio
    async def test_callback_not_fired_when_no_auth_cookies(self, tmp_path):
        from observer.auth_registry import AuthRegistry

        reg = AuthRegistry(cdp=_FakeCDPClient(), data_dir=tmp_path)
        cb = AsyncMock()
        reg.set_auth_callback(cb)

        # Cookie with no auth signals
        cookies = [
            {
                "name": "analytics_id",
                "domain": "example.com",
                "httpOnly": False,
                "secure": False,
                "expires": 9999999999,
                "value": "xyz",
                "path": "/",
            }
        ]
        await reg._detect_auth_cookies("example.com", cookies)
        await asyncio.sleep(0)

        cb.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_callback_receives_correct_entry_data(self, tmp_path):
        from observer.auth_registry import AuthRegistry

        reg = AuthRegistry(cdp=_FakeCDPClient(), data_dir=tmp_path)
        received = {}

        async def on_auth(domain, entry):
            received["domain"] = domain
            received["entry"] = entry

        reg.set_auth_callback(on_auth)

        cookies = [
            {
                "name": "sid",
                "domain": "myapp.io",
                "httpOnly": True,
                "secure": True,
                "expires": -1,
                "value": "token_xyz",
                "path": "/",
            }
        ]
        await reg._detect_auth_cookies("myapp.io", cookies)
        await asyncio.sleep(0)

        assert received["domain"] == "myapp.io"
        assert received["entry"].domain == "myapp.io"
        assert received["entry"].authenticated is True
        assert "sid" in received["entry"].session_cookie_names

    @pytest.mark.asyncio
    async def test_failing_callback_does_not_propagate(self, tmp_path):
        """A callback that raises must not abort auth detection."""
        from observer.auth_registry import AuthRegistry

        reg = AuthRegistry(cdp=_FakeCDPClient(), data_dir=tmp_path)

        async def bad_callback(domain, entry):
            raise RuntimeError("broadcast failure")

        reg.set_auth_callback(bad_callback)

        cookies = [
            {
                "name": "session",
                "domain": "example.com",
                "httpOnly": True,
                "secure": True,
                "expires": -1,
                "value": "abc",
                "path": "/",
            }
        ]
        # Detection itself should complete without raising
        await reg._detect_auth_cookies("example.com", cookies)
        await asyncio.sleep(0)

        # The domain should still be registered despite the bad callback
        assert "example.com" in reg._registry


# ---------------------------------------------------------------------------
# ObserverManager — _on_auth_detected calls ws_broadcast
# ---------------------------------------------------------------------------

class TestObserverManagerBroadcast:
    @pytest.mark.asyncio
    async def test_on_auth_detected_calls_broadcast(self, tmp_path):
        from observer.manager import ObserverManager
        from observer.auth_registry import AuthEntry
        from datetime import datetime, timezone

        manager = ObserverManager(port=9222, data_dir=tmp_path)

        entry = AuthEntry(
            domain="example.com",
            authenticated=True,
            detected_at=datetime.now(timezone.utc).isoformat(),
            cookies_count=3,
            session_cookie_names=["session"],
            expires_at=None,
        )

        # Patch the broadcast function inside usr.plugins.phantom_bridge.ws_broadcast
        mock_broadcast = AsyncMock()
        fake_ws_mod = ModuleType("usr.plugins.phantom_bridge.ws_broadcast")
        fake_ws_mod.broadcast = mock_broadcast

        with patch.dict(sys.modules, {
            "usr": MagicMock(),
            "usr.plugins": MagicMock(),
            "usr.plugins.phantom_bridge": MagicMock(),
            "usr.plugins.phantom_bridge.ws_broadcast": fake_ws_mod,
        }):
            await manager._on_auth_detected("example.com", entry)

        mock_broadcast.assert_awaited_once()
        event_type, data = mock_broadcast.call_args.args
        assert event_type == "phantom_bridge_auth"
        assert data["domain"] == "example.com"
        assert data["authenticated"] is True
        assert data["cookies_count"] == 3

    @pytest.mark.asyncio
    async def test_on_auth_detected_survives_import_error(self, tmp_path):
        """If ws_broadcast can't be imported, the method must not raise."""
        from observer.manager import ObserverManager
        from observer.auth_registry import AuthEntry
        from datetime import datetime, timezone

        manager = ObserverManager(port=9222, data_dir=tmp_path)
        entry = AuthEntry(
            domain="example.com",
            authenticated=True,
            detected_at=datetime.now(timezone.utc).isoformat(),
            cookies_count=1,
        )

        with patch.dict(sys.modules, {"usr": None}):
            # Should not raise
            await manager._on_auth_detected("example.com", entry)
