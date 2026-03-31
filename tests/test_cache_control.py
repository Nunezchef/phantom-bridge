"""Tests for Cache-Control: no-store header on all BridgeHandler responses.

A0 v1.5 enables API caching by default. BridgeHandler overrides handle_request
to inject Cache-Control: no-store so that status, cookies, and auth data are
never served stale.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub out A0 framework so api/bridge.py can be imported
# ---------------------------------------------------------------------------

def _install_stubs():
    # helpers package
    helpers_mod = ModuleType("helpers")
    helpers_api_mod = ModuleType("helpers.api")

    class _FakeResponse:
        """Minimal Flask-Response-like object."""
        def __init__(self, response="", status=200, mimetype="application/json"):
            self.response = response
            self.status = status
            self.mimetype = mimetype
            self.headers = {}

    class _ApiHandler:
        def __init__(self, app=None, thread_lock=None):
            pass
        @classmethod
        def requires_auth(cls): return True
        @classmethod
        def requires_csrf(cls): return True
        async def process(self, input, request): return {}
        async def handle_request(self, request):
            output = await self.process({}, request)
            if isinstance(output, _FakeResponse):
                return output
            return _FakeResponse(response=str(output))

    helpers_api_mod.ApiHandler = _ApiHandler
    helpers_api_mod.Request = MagicMock
    # Use the same name A0 uses so api/bridge.py's type annotation resolves
    helpers_api_mod.Response = _FakeResponse

    helpers_mod.api = helpers_api_mod
    sys.modules.setdefault("helpers", helpers_mod)
    sys.modules.setdefault("helpers.api", helpers_api_mod)

    return _FakeResponse


_FakeResponse = _install_stubs()


# ---------------------------------------------------------------------------
# Import the handler under test
# ---------------------------------------------------------------------------

# We need to prevent the import of usr.plugins.* at module level
# (those only resolve inside the A0 container). They're only used inside
# method bodies with local imports, so a plain import works fine here.
from api.bridge import BridgeHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler():
    """Return a BridgeHandler with a minimal fake process() override."""
    handler = BridgeHandler.__new__(BridgeHandler)
    return handler


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCacheControlHeader:

    @pytest.mark.asyncio
    async def test_status_action_has_no_store(self):
        handler = _make_handler()
        # Stub process to return a plain dict (normal path)
        handler.process = AsyncMock(return_value={"ok": True, "running": False})
        fake_req = MagicMock()
        response = await handler.handle_request(fake_req)
        assert response.headers.get("Cache-Control") == "no-store"

    @pytest.mark.asyncio
    async def test_cookies_action_has_no_store(self):
        handler = _make_handler()
        handler.process = AsyncMock(return_value={"ok": True, "cookies": {}})
        response = await handler.handle_request(MagicMock())
        assert response.headers.get("Cache-Control") == "no-store"

    @pytest.mark.asyncio
    async def test_auth_registry_action_has_no_store(self):
        handler = _make_handler()
        handler.process = AsyncMock(return_value={"ok": True, "registry": {}})
        response = await handler.handle_request(MagicMock())
        assert response.headers.get("Cache-Control") == "no-store"

    @pytest.mark.asyncio
    async def test_error_response_also_has_no_store(self):
        handler = _make_handler()
        handler.process = AsyncMock(return_value={"ok": False, "error": "boom"})
        response = await handler.handle_request(MagicMock())
        assert response.headers.get("Cache-Control") == "no-store"

    @pytest.mark.asyncio
    async def test_header_value_is_exactly_no_store(self):
        """Ensure we didn't accidentally add extra directives."""
        handler = _make_handler()
        handler.process = AsyncMock(return_value={})
        response = await handler.handle_request(MagicMock())
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.asyncio
    async def test_existing_headers_preserved(self):
        """The no-store header must not wipe out other response headers."""
        handler = _make_handler()
        handler.process = AsyncMock(return_value={})
        response = await handler.handle_request(MagicMock())
        # Set a pre-existing header as if super() had added it
        response.headers["X-Custom"] = "yes"
        # Both headers must coexist
        assert response.headers.get("Cache-Control") == "no-store"
        assert response.headers.get("X-Custom") == "yes"

    @pytest.mark.asyncio
    async def test_header_present_when_process_returns_response_object(self):
        """If process() already returns a Response, the override still applies."""
        handler = _make_handler()
        pre_built = _FakeResponse(response='{"ok":true}', status=200)
        handler.process = AsyncMock(return_value=pre_built)
        response = await handler.handle_request(MagicMock())
        assert response.headers.get("Cache-Control") == "no-store"
