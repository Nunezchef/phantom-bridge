"""Tests for Unicode sanitization in sitemap_learner.py and playbook_recorder.py.

Lone Unicode surrogates (U+D800–U+DFFF) appear in some web page titles and
form field values due to malformed UTF-16 encoding.  Python's json.dumps
raises on these; our _safe_str helper strips them via UTF-8 round-trip.
"""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# _safe_str from sitemap_learner
# ---------------------------------------------------------------------------

from observer.sitemap_learner import _safe_str as sitemap_safe_str


class TestSafeSStrSitemap:
    def test_normal_string_unchanged(self):
        assert sitemap_safe_str("Hello world") == "Hello world"

    def test_empty_string_unchanged(self):
        assert sitemap_safe_str("") == ""

    def test_lone_surrogate_replaced(self):
        bad = "title\ud800end"
        result = sitemap_safe_str(bad)
        assert "\ud800" not in result

    def test_result_is_json_serializable(self):
        bad = "data\ud83d\ude00broken\udc00end"
        result = sitemap_safe_str(bad)
        # Must not raise
        json.dumps(result)

    def test_valid_emoji_preserved(self):
        # Real multi-byte emoji should survive unharmed
        emoji = "Hello \U0001f600 world"
        assert sitemap_safe_str(emoji) == emoji

    def test_chinese_characters_preserved(self):
        text = "页面标题"
        assert sitemap_safe_str(text) == text

    def test_multiple_lone_surrogates_all_replaced(self):
        bad = "\ud800\ud801\udc00"
        result = sitemap_safe_str(bad)
        for surrogate in ["\ud800", "\ud801", "\udc00"]:
            assert surrogate not in result

    def test_replacement_char_used(self):
        bad = "\ud800"
        result = sitemap_safe_str(bad)
        # UTF-8 errors='replace' replaces invalid bytes — the surrogate must be gone
        assert "\ud800" not in result
        assert len(result) > 0  # replaced with something (? or \ufffd depending on Python version)


# ---------------------------------------------------------------------------
# _safe_str from playbook_recorder
# ---------------------------------------------------------------------------

from observer.playbook_recorder import _safe_str as recorder_safe_str


class TestSafeStrRecorder:
    def test_normal_string_unchanged(self):
        assert recorder_safe_str("click me") == "click me"

    def test_lone_surrogate_in_selector_replaced(self):
        bad = "#btn\ud800value"
        result = recorder_safe_str(bad)
        assert "\ud800" not in result

    def test_lone_surrogate_in_typed_value_replaced(self):
        bad = "user input\ud83d broken"
        result = recorder_safe_str(bad)
        assert "\ud83d" not in result

    def test_result_is_json_serializable(self):
        bad = "value\ud800\udc00"
        result = recorder_safe_str(bad)
        json.dumps(result)

    def test_password_mask_not_affected(self):
        # Passwords are already masked to *** before reaching our code
        assert recorder_safe_str("***") == "***"


# ---------------------------------------------------------------------------
# Integration: sitemap_learner._record_visit with bad title
# ---------------------------------------------------------------------------

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from observer.sitemap_learner import SitemapLearner


class TestSitemapLearnerBadTitle:
    def _make_learner(self, tmp_path: Path) -> SitemapLearner:
        cdp = MagicMock()
        cdp.subscribe = AsyncMock()
        return SitemapLearner(cdp=cdp, data_dir=tmp_path)

    def test_record_visit_with_lone_surrogate_title(self, tmp_path):
        learner = self._make_learner(tmp_path)
        bad_title = "Page \ud800 Title"
        learner._record_visit("https://example.com/dashboard", bad_title)

        sm = learner._sitemaps.get("example.com")
        assert sm is not None
        # Find the stored title
        pv = sm._pages.get("/dashboard")
        assert pv is not None
        stored = pv.titles[0]
        assert "\ud800" not in stored

    def test_record_visit_title_is_json_serializable(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner._record_visit("https://example.com/page", "Bad \ud800 title")
        sm = learner._sitemaps["example.com"]
        # Should not raise
        from observer.sitemap_learner import _sitemap_to_dict
        d = _sitemap_to_dict(sm)
        json.dumps(d)

    def test_record_visit_normal_title_preserved(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner._record_visit("https://example.com/", "Normal Title")
        pv = learner._sitemaps["example.com"]._pages["/"]
        assert pv.titles[0] == "Normal Title"


# ---------------------------------------------------------------------------
# Integration: playbook_recorder DOM event handling with bad strings
# ---------------------------------------------------------------------------

from observer.playbook_recorder import PlaybookRecorder


class _FakeCDP:
    async def subscribe(self, event, cb): pass
    async def send(self, method, params=None): return {}
    async def _listen(self): pass


class TestPlaybookRecorderBadStrings:
    def _make_recorder(self, tmp_path: Path) -> PlaybookRecorder:
        return PlaybookRecorder(cdp=_FakeCDP(), data_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_click_with_lone_surrogate_text(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec._recording = True
        rec._current_name = "test"

        bad_data = {
            "type": "click",
            "selector": "#btn",
            "text": "Click \ud800 me",
            "url": "https://example.com/",
        }
        await rec._on_binding_called({"name": "__phantomBridge", "payload": json.dumps(bad_data)})

        assert len(rec._current_steps) == 1
        step = rec._current_steps[0]
        assert "\ud800" not in (step.text or "")

    @pytest.mark.asyncio
    async def test_type_with_lone_surrogate_value(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec._recording = True
        rec._current_name = "test"

        bad_data = {
            "type": "type",
            "selector": "input[name='q']",
            "value": "search \ud800 term",
            "url": "https://example.com/",
        }
        await rec._on_binding_called({"name": "__phantomBridge", "payload": json.dumps(bad_data)})

        step = rec._current_steps[0]
        assert "\ud800" not in step.value

    @pytest.mark.asyncio
    async def test_step_value_is_json_serializable(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec._recording = True
        rec._current_name = "test"

        bad_data = {
            "type": "type",
            "selector": "#q",
            "value": "bad\ud800value",
            "url": "https://x.com/",
        }
        await rec._on_binding_called({"name": "__phantomBridge", "payload": json.dumps(bad_data)})
        step = rec._current_steps[0]
        # Must not raise
        json.dumps({"value": step.value, "text": step.text})

    @pytest.mark.asyncio
    async def test_not_recording_ignores_event(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec._recording = False

        data = {"type": "click", "selector": "#btn", "text": "hi", "url": "https://x.com/"}
        await rec._on_binding_called({"name": "__phantomBridge", "payload": json.dumps(data)})
        assert rec._current_steps == []
