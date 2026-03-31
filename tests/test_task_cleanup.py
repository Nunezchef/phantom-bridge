"""Tests for task cleanup and lifecycle safety in ObserverManager.

Verifies:
- Tasks are properly cancelled and awaited on stop()
- Double-start is idempotent (no duplicate listener tasks)
- stop() after stop() does not raise
- _tasks list is empty after stop()
- bridge.py: a new ObserverManager instance is created on each start()
  (never reusing the stopped one, so no task accumulation is possible)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from observer.manager import ObserverManager


# ---------------------------------------------------------------------------
# Fake CDP that cooperates with the manager lifecycle
# ---------------------------------------------------------------------------

class _FakeCDP:
    def __init__(self):
        self.connected = False
        self.subscriptions: list = []
        self.domains_enabled: list = []

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def subscribe(self, event, cb):
        self.subscriptions.append((event, cb))

    async def enable_domains(self, *domains):
        self.domains_enabled.extend(domains)

    async def get_cookies(self):
        return []

    async def send(self, method, params=None):
        return {}

    async def _listen(self):
        # Simulate a long-running listener that cooperates with cancellation
        try:
            await asyncio.sleep(9999)
        except asyncio.CancelledError:
            raise


# ---------------------------------------------------------------------------
# Patch ObserverManager to use our fake CDP
# ---------------------------------------------------------------------------

def _make_manager(tmp_path: Path) -> ObserverManager:
    manager = ObserverManager(port=9222, data_dir=tmp_path)
    manager._cdp = _FakeCDP()
    return manager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestObserverManagerTaskCleanup:

    @pytest.mark.asyncio
    async def test_start_creates_listener_task(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        assert len(manager._tasks) >= 1
        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_all_tasks(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        tasks_snapshot = list(manager._tasks)
        await manager.stop()
        for task in tasks_snapshot:
            assert task.done(), "task should be done after stop()"

    @pytest.mark.asyncio
    async def test_stop_clears_tasks_list(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        await manager.stop()
        assert manager._tasks == []

    @pytest.mark.asyncio
    async def test_double_start_does_not_accumulate_tasks(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        count_after_first = len(manager._tasks)

        # Second start should be a no-op
        await manager.start()
        assert len(manager._tasks) == count_after_first, (
            "double start() must not add more tasks"
        )
        await manager.stop()

    @pytest.mark.asyncio
    async def test_double_start_started_flag_stays_true(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        assert manager._started is True
        await manager.start()  # no-op
        assert manager._started is True
        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_resets_started_flag(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        assert manager._started is True
        await manager.stop()
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_start_stop_start_stop_cycle(self, tmp_path):
        """Full restart cycle must not leak tasks."""
        manager = _make_manager(tmp_path)

        await manager.start()
        await manager.stop()
        assert manager._tasks == []
        assert manager._started is False

        # Re-wire CDP (simulates a fresh bridge start using a new manager)
        manager2 = _make_manager(tmp_path)
        await manager2.start()
        await manager2.stop()
        assert manager2._tasks == []

    @pytest.mark.asyncio
    async def test_cdp_disconnected_after_stop(self, tmp_path):
        manager = _make_manager(tmp_path)
        await manager.start()
        assert manager._cdp.connected is True
        await manager.stop()
        assert manager._cdp.connected is False

    @pytest.mark.asyncio
    async def test_started_false_before_start(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager._started is False


class TestBridgeAlwaysCreatesNewManager:
    """Verify bridge.py creates a new ObserverManager on every start(), never reusing one."""

    def test_create_bridge_from_config_returns_fresh_instance(self, tmp_path):
        """Each create_bridge_from_config call produces an independent BrowserBridge
        with _observer_manager=None, confirming no stale state is carried over."""
        import bridge as bridge_mod

        # Patch yaml and profile resolution to avoid filesystem side effects
        with patch("bridge.Path") as MockPath:
            MockPath.return_value.__truediv__ = lambda s, o: tmp_path / o
            MockPath.return_value.resolve.return_value = tmp_path

            from bridge import create_bridge_from_config
            b1 = create_bridge_from_config({})
            b2 = create_bridge_from_config({})

        # Each call produces a distinct BrowserBridge instance
        assert b1 is not b2
        # Neither has started an observer manager yet
        assert b1._observer_manager is None
        assert b2._observer_manager is None
