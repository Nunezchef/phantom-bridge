"""Tests for self-correction-friendly error messages in bridge_record and bridge_replay.

A0 v1.5 agents attempt to self-correct malformed tool calls by feeding error
messages back into the next inference step. Error messages must include the
correct JSON call format so the model can recover without human help.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub A0 framework (helpers.tool) so we can import the tool modules
# ---------------------------------------------------------------------------

def _install_tool_stubs():
    helpers_mod = ModuleType("helpers")
    helpers_tool_mod = ModuleType("helpers.tool")

    class _Response:
        def __init__(self, message: str, break_loop: bool = False):
            self.message = message
            self.break_loop = break_loop

    class _Tool:
        def __init__(self):
            self.args: dict = {}
            self.agent = MagicMock()

        async def execute(self, **kwargs):
            raise NotImplementedError

    helpers_tool_mod.Tool = _Tool
    helpers_tool_mod.Response = _Response
    helpers_mod.tool = helpers_tool_mod
    sys.modules.setdefault("helpers", helpers_mod)
    sys.modules.setdefault("helpers.tool", helpers_tool_mod)

    return _Response


_Response = _install_tool_stubs()


from tools.bridge_record import BridgeRecord
from tools.bridge_replay import BridgeReplay


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record_tool(args: dict, recorder=None):
    tool = BridgeRecord.__new__(BridgeRecord)
    tool.args = args
    tool.agent = MagicMock()
    # Patch _get_recorder
    tool._get_recorder = MagicMock(return_value=recorder)
    return tool


def _make_replay_tool(args: dict, recorder=None):
    tool = BridgeReplay.__new__(BridgeReplay)
    tool.args = args
    tool.agent = MagicMock()
    tool._get_recorder = MagicMock(return_value=recorder)
    tool._check_session_health = AsyncMock(return_value=None)
    tool._get_profile_dir = MagicMock(return_value="/data/profile")
    return tool


# ---------------------------------------------------------------------------
# bridge_record error messages
# ---------------------------------------------------------------------------

class TestBridgeRecordErrors:

    @pytest.mark.asyncio
    async def test_invalid_action_includes_json_examples(self):
        tool = _make_record_tool({"action": "badaction"})
        resp = await tool.execute()
        assert '{"tool":"bridge_record"' in resp.message
        assert '"action":"start"' in resp.message
        assert '"action":"list"' in resp.message

    @pytest.mark.asyncio
    async def test_missing_name_for_start_includes_json_example(self):
        recorder = MagicMock()
        tool = _make_record_tool({"action": "start", "name": ""}, recorder=recorder)
        resp = await tool.execute()
        assert '{"tool":"bridge_record","action":"start","name":' in resp.message

    @pytest.mark.asyncio
    async def test_missing_name_for_delete_includes_json_example(self):
        recorder = MagicMock()
        tool = _make_record_tool({"action": "delete", "name": ""}, recorder=recorder)
        resp = await tool.execute()
        assert '{"tool":"bridge_record","action":"delete","name":' in resp.message

    @pytest.mark.asyncio
    async def test_recorder_unavailable_suggests_bridge_open(self):
        tool = _make_record_tool({"action": "start", "name": "x"}, recorder=None)
        resp = await tool.execute()
        assert '{"tool":"browser_bridge_open"}' in resp.message

    @pytest.mark.asyncio
    async def test_invalid_action_break_loop_is_false(self):
        tool = _make_record_tool({"action": "???"})
        resp = await tool.execute()
        assert resp.break_loop is False

    @pytest.mark.asyncio
    async def test_missing_name_break_loop_is_false(self):
        recorder = MagicMock()
        tool = _make_record_tool({"action": "start"}, recorder=recorder)
        resp = await tool.execute()
        assert resp.break_loop is False

    @pytest.mark.asyncio
    async def test_invalid_action_lists_all_four_actions(self):
        tool = _make_record_tool({"action": "unknown"})
        resp = await tool.execute()
        for action in ("start", "stop", "list", "delete"):
            assert action in resp.message


# ---------------------------------------------------------------------------
# bridge_replay error messages
# ---------------------------------------------------------------------------

class TestBridgeReplayErrors:

    @pytest.mark.asyncio
    async def test_missing_name_includes_json_example(self):
        tool = _make_replay_tool({"name": ""})
        resp = await tool.execute()
        assert '{"tool":"bridge_replay","name":' in resp.message

    @pytest.mark.asyncio
    async def test_missing_name_suggests_list_command(self):
        tool = _make_replay_tool({"name": ""})
        resp = await tool.execute()
        assert '{"tool":"bridge_record","action":"list"}' in resp.message

    @pytest.mark.asyncio
    async def test_recorder_unavailable_suggests_bridge_open(self):
        tool = _make_replay_tool({"name": "workflow"}, recorder=None)
        resp = await tool.execute()
        assert '{"tool":"browser_bridge_open"}' in resp.message

    @pytest.mark.asyncio
    async def test_playbook_not_found_lists_available(self):
        recorder = MagicMock()
        recorder.get_playbook = MagicMock(return_value=None)
        recorder.list_playbooks = MagicMock(return_value=[
            {"name": "checkout_flow"},
            {"name": "login_github"},
        ])
        tool = _make_replay_tool({"name": "nonexistent"}, recorder=recorder)
        resp = await tool.execute()
        assert "checkout_flow" in resp.message or "login_github" in resp.message

    @pytest.mark.asyncio
    async def test_missing_name_break_loop_is_false(self):
        tool = _make_replay_tool({"name": ""})
        resp = await tool.execute()
        assert resp.break_loop is False

    @pytest.mark.asyncio
    async def test_recorder_unavailable_break_loop_is_false(self):
        tool = _make_replay_tool({"name": "x"}, recorder=None)
        resp = await tool.execute()
        assert resp.break_loop is False
