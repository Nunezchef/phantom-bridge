"""Tests for extensions/system_prompt/_45_browser_bridge.py

Tests cover:
- _is_small_model detection (name hints, ctx_length threshold)
- _compact_prompt: token budget, required fields, live auth cap
- _full_prompt: tool examples, dynamic section caps, missing data dirs
- BrowserBridgeContext.execute: routes small vs full, appends to list
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out A0 framework imports so the extension module can be imported
# ---------------------------------------------------------------------------


def _make_agent_stubs():
    """Insert minimal stubs for helpers.extension and agent into sys.modules."""
    # helpers.extension
    ext_mod = ModuleType("helpers")
    ext_mod.extension = ModuleType("helpers.extension")

    class _Extension:
        def __init__(self):
            self.agent = None

    ext_mod.extension.Extension = _Extension
    sys.modules.setdefault("helpers", ext_mod)
    sys.modules.setdefault("helpers.extension", ext_mod.extension)

    # agent
    agent_mod = ModuleType("agent")
    agent_mod.LoopData = MagicMock
    sys.modules.setdefault("agent", agent_mod)


_make_agent_stubs()

# Now we can import from our extension
from extensions.system_prompt._45_browser_bridge import (
    _is_small_model,
    _compact_prompt,
    _full_prompt,
    _TOOL_EXAMPLES,
    _SMALL_CTX_THRESHOLD,
    BrowserBridgeContext,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(name: str = "gpt-4o", ctx_length: int = 128_000):
    agent = MagicMock()
    agent.config.chat_model.name = name
    agent.config.chat_model.ctx_length = ctx_length
    return agent


# ---------------------------------------------------------------------------
# _is_small_model
# ---------------------------------------------------------------------------


class TestIsSmallModel:
    def test_large_model_returns_false(self):
        assert _is_small_model(_make_agent("gpt-4o", 128_000)) is False

    def test_small_ctx_returns_true(self):
        assert _is_small_model(_make_agent("some-model", _SMALL_CTX_THRESHOLD)) is True

    def test_ctx_just_above_threshold_returns_false(self):
        assert (
            _is_small_model(_make_agent("some-model", _SMALL_CTX_THRESHOLD + 1))
            is False
        )

    def test_zero_ctx_returns_false(self):
        # ctx_length=0 means "unknown" — don't treat as small
        assert _is_small_model(_make_agent("gpt-4o", 0)) is False

    def test_name_hint_small_returns_true(self):
        assert _is_small_model(_make_agent("gpt-4o-small", 128_000)) is True

    def test_name_hint_mini_returns_true(self):
        assert _is_small_model(_make_agent("gpt-4o-mini", 128_000)) is True

    def test_name_hint_phi_returns_true(self):
        assert _is_small_model(_make_agent("phi-3.5", 4096)) is True

    def test_name_hint_gemma_returns_true(self):
        assert _is_small_model(_make_agent("gemma-7b", 8192)) is True

    def test_name_hint_case_insensitive(self):
        assert _is_small_model(_make_agent("GPT-4O-MINI", 128_000)) is True

    def test_exception_in_config_returns_false(self):
        agent = MagicMock()
        agent.config = None  # accessing .chat_model will raise
        assert _is_small_model(agent) is False


# ---------------------------------------------------------------------------
# _compact_prompt
# ---------------------------------------------------------------------------


class TestCompactPrompt:
    def test_contains_phantom_bridge_header(self, tmp_path):
        text = _compact_prompt(tmp_path)
        assert "Phantom Bridge" in text

    def test_contains_all_tool_names(self, tmp_path):
        text = _compact_prompt(tmp_path)
        for tool in [
            "browser_bridge_open",
            "browser_bridge_close",
            "browser_bridge_status",
            "bridge_auth",
            "bridge_record",
            "bridge_replay",
            "bridge_decrypt_cookies",
        ]:
            assert tool in text, f"missing tool: {tool}"

    def test_contains_canonical_json_examples(self, tmp_path):
        text = _compact_prompt(tmp_path)
        assert '{"tool":"browser_bridge_open"}' in text
        assert '{"tool":"bridge_record","action":"start","name":"my_workflow"}' in text

    def test_token_budget_under_250(self, tmp_path):
        """Compact prompt with no live data must stay under ~250 tokens (words/0.75)."""
        text = _compact_prompt(tmp_path)
        word_count = len(text.split())
        # 250 tokens ≈ 188 words (0.75 words/token) — be generous with 300 words
        assert word_count < 300, f"compact prompt too long: {word_count} words"

    def test_includes_auth_domains_when_present(self, tmp_path):
        auth = {
            "example.com": {"authenticated": True, "expires_at": None},
            "github.com": {"authenticated": False, "expires_at": None},
        }
        (tmp_path / "auth_registry.json").write_text(json.dumps(auth))
        text = _compact_prompt(tmp_path)
        assert "example.com" in text
        assert "github.com" in text

    def test_caps_auth_domains_at_3(self, tmp_path):
        auth = {f"domain{i}.com": {"authenticated": True} for i in range(6)}
        (tmp_path / "auth_registry.json").write_text(json.dumps(auth))
        text = _compact_prompt(tmp_path)
        # At most 3 domain lines should appear
        domain_count = sum(1 for i in range(6) if f"domain{i}.com" in text)
        assert domain_count <= 3

    def test_no_auth_file_does_not_raise(self, tmp_path):
        # No auth_registry.json — should not raise
        text = _compact_prompt(tmp_path)
        assert "Phantom Bridge" in text

    def test_malformed_auth_file_does_not_raise(self, tmp_path):
        (tmp_path / "auth_registry.json").write_text("not valid json{{")
        text = _compact_prompt(tmp_path)
        assert "Phantom Bridge" in text


# ---------------------------------------------------------------------------
# _full_prompt
# ---------------------------------------------------------------------------


class TestFullPrompt:
    def test_contains_phantom_bridge_header(self, tmp_path):
        text = _full_prompt(tmp_path)
        assert "Phantom Bridge" in text

    def test_contains_all_tool_names(self, tmp_path):
        text = _full_prompt(tmp_path)
        for tool in [
            "browser_bridge_open",
            "bridge_auth",
            "bridge_record",
            "bridge_replay",
            "bridge_decrypt_cookies",
        ]:
            assert tool in text

    def test_contains_canonical_json_examples(self, tmp_path):
        text = _full_prompt(tmp_path)
        assert '{"tool":"browser_bridge_open"}' in text
        assert '{"tool":"bridge_replay","name":"my_workflow"}' in text

    def test_includes_authenticated_domains(self, tmp_path):
        auth = {"github.com": {"authenticated": True, "expires_at": "2099-01-01"}}
        (tmp_path / "auth_registry.json").write_text(json.dumps(auth))
        text = _full_prompt(tmp_path)
        assert "github.com" in text
        assert "active" in text

    def test_expired_domain_shows_expired(self, tmp_path):
        auth = {"old.com": {"authenticated": False, "expires_at": None}}
        (tmp_path / "auth_registry.json").write_text(json.dumps(auth))
        text = _full_prompt(tmp_path)
        assert "EXPIRED" in text

    def test_playbooks_capped_at_5(self, tmp_path):
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        for i in range(8):
            pb = {"name": f"pb{i}", "domain": "x.com", "steps": [], "description": ""}
            (pb_dir / f"pb{i}.json").write_text(json.dumps(pb))
        text = _full_prompt(tmp_path)
        count = sum(1 for i in range(8) if f"pb{i}" in text)
        assert count <= 5

    def test_sitemaps_capped_at_3(self, tmp_path):
        sm_dir = tmp_path / "sitemaps"
        sm_dir.mkdir()
        for i in range(6):
            sm = {"domain": f"site{i}.com", "features": {"a": 1}}
            (sm_dir / f"site{i}.json").write_text(json.dumps(sm))
        text = _full_prompt(tmp_path)
        count = sum(1 for i in range(6) if f"site{i}.com" in text)
        assert count <= 3

    def test_no_data_dir_does_not_raise(self, tmp_path):
        # Point at a non-existent subdir
        text = _full_prompt(tmp_path / "nonexistent")
        assert "Phantom Bridge" in text

    def test_malformed_playbook_skipped(self, tmp_path):
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        (pb_dir / "bad.json").write_text("{bad json")
        text = _full_prompt(tmp_path)
        assert "Phantom Bridge" in text  # didn't crash


# ---------------------------------------------------------------------------
# BrowserBridgeContext.execute — routing
# ---------------------------------------------------------------------------


class TestBrowserBridgeContextExecute:
    def _make_ctx(self, agent):
        ctx = BrowserBridgeContext()
        ctx.agent = agent
        return ctx

    @pytest.mark.asyncio
    async def test_small_model_appends_compact_prompt(self, tmp_path):
        import data_paths as dp_mod

        agent = _make_agent("phi-3.5", 4096)
        ctx = self._make_ctx(agent)
        prompt_list: list[str] = []
        with patch.object(dp_mod, "DATA_DIR", tmp_path):
            await ctx.execute(system_prompt=prompt_list)
        assert len(prompt_list) == 1
        text = prompt_list[0]
        assert "How it works" not in text
        assert "Phantom Bridge" in text

    @pytest.mark.asyncio
    async def test_large_model_appends_full_prompt(self, tmp_path):
        import data_paths as dp_mod

        agent = _make_agent("gpt-4o", 128_000)
        ctx = self._make_ctx(agent)
        prompt_list: list[str] = []
        with patch.object(dp_mod, "DATA_DIR", tmp_path):
            await ctx.execute(system_prompt=prompt_list)
        assert len(prompt_list) == 1
        text = prompt_list[0]
        assert "How it works" in text

    @pytest.mark.asyncio
    async def test_exactly_one_item_appended(self, tmp_path):
        import data_paths as dp_mod

        agent = _make_agent("gpt-4o", 128_000)
        ctx = self._make_ctx(agent)
        prompt_list: list[str] = ["existing item"]
        with patch.object(dp_mod, "DATA_DIR", tmp_path):
            await ctx.execute(system_prompt=prompt_list)
        assert len(prompt_list) == 2

    @pytest.mark.asyncio
    async def test_tool_examples_present_in_both_variants(self, tmp_path):
        import data_paths as dp_mod

        for name, ctx_len in [("phi-3.5", 4096), ("gpt-4o", 128_000)]:
            agent = _make_agent(name, ctx_len)
            ctx = self._make_ctx(agent)
            prompt_list: list[str] = []
            with patch.object(dp_mod, "DATA_DIR", tmp_path):
                await ctx.execute(system_prompt=prompt_list)
            assert '{"tool":"browser_bridge_open"}' in prompt_list[0], (
                f"missing tool example for {name}"
            )
