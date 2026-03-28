"""
Playbook Recorder — records user browser actions as replayable playbooks.

Subscribes to CDP events (Page navigation, Network requests) and captures
them as a sequence of PlaybookSteps.  Pure observation — never interferes
with user browsing.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from observer.cdp_client import CDPClient
from observer.playbook import Playbook, PlaybookStep, slugify

logger = logging.getLogger("phantom_bridge")

# File extensions to ignore when recording network requests
_STATIC_EXTENSIONS = frozenset({
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".webp", ".avif",
})

# HTTP methods worth recording (skip GET — too noisy)
_RECORDED_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


class PlaybookRecorder:
    """Records user browser actions as replayable playbooks."""

    def __init__(self, cdp: CDPClient, data_dir: Path):
        self._cdp = cdp
        self._data_dir = data_dir / "playbooks"
        self._recording: bool = False
        self._current_steps: list[PlaybookStep] = []
        self._current_name: str | None = None
        self._record_start: float | None = None
        self._last_step_time: float | None = None
        self._current_domain: str = ""
        self._playbooks: dict[str, Playbook] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialize — load existing playbooks from disk.

        Does NOT subscribe to CDP events yet.  Recording only begins
        when start_recording() is called.
        """
        self._load_all()
        logger.info(
            "playbook_recorder: initialized with %d saved playbooks",
            len(self._playbooks),
        )

    async def stop(self) -> None:
        """Stop recording if active, persist everything."""
        if self._recording:
            await self.stop_recording()
        self._save_all()

    # ------------------------------------------------------------------
    # Recording controls
    # ------------------------------------------------------------------

    async def start_recording(self, name: str) -> None:
        """Start recording a new playbook.

        Subscribes to CDP events for navigation and network activity.
        """
        if self._recording:
            raise RuntimeError(
                f"Already recording playbook '{self._current_name}'. "
                "Stop current recording first."
            )

        slug = slugify(name)
        if not slug:
            raise ValueError("Playbook name cannot be empty")

        self._current_name = slug
        self._current_steps = []
        self._record_start = time.time()
        self._last_step_time = self._record_start
        self._current_domain = ""
        self._recording = True

        # Enable CDP domains we need
        await self._cdp.send("Page.enable")
        await self._cdp.send("Network.enable")

        # Subscribe to events
        await self._cdp.subscribe("Page.frameNavigated", self._on_navigated)
        await self._cdp.subscribe(
            "Page.navigatedWithinDocument", self._on_spa_navigation
        )
        await self._cdp.subscribe(
            "Network.requestWillBeSent", self._on_network_request
        )
        await self._cdp.subscribe(
            "Network.responseReceived", self._on_network_response
        )

        logger.info("playbook_recorder: recording started — '%s'", slug)

    async def stop_recording(self, description: str = "") -> Playbook:
        """Stop recording, finalize the playbook, and persist to disk.

        Returns the completed Playbook.
        """
        if not self._recording:
            raise RuntimeError("No recording in progress")

        self._recording = False
        now = time.time()
        duration_ms = int((now - (self._record_start or now)) * 1000)

        playbook = Playbook(
            name=self._current_name or "unnamed",
            domain=self._current_domain,
            description=description,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            steps=list(self._current_steps),
            duration_ms=duration_ms,
        )

        self._playbooks[playbook.name] = playbook
        self._save_playbook(playbook)

        step_count = len(playbook.steps)
        logger.info(
            "playbook_recorder: recording stopped — '%s' (%d steps, %dms)",
            playbook.name,
            step_count,
            duration_ms,
        )

        # Reset state
        self._current_steps = []
        self._current_name = None
        self._record_start = None
        self._last_step_time = None

        return playbook

    # ------------------------------------------------------------------
    # CDP event handlers
    # ------------------------------------------------------------------

    async def _on_navigated(self, params: dict[str, Any]) -> None:
        """Record a navigate step from Page.frameNavigated."""
        if not self._recording:
            return

        frame = params.get("frame", {})
        # Only record top-level frame navigations
        if frame.get("parentId"):
            return

        url = frame.get("url", "")
        if not url or url in ("about:blank", "about:srcdoc"):
            return

        # Extract domain from first navigation
        if not self._current_domain and "://" in url:
            self._current_domain = url.split("://", 1)[1].split("/", 1)[0]

        self._add_step(PlaybookStep(
            action="navigate",
            timestamp=datetime.now(timezone.utc).isoformat(),
            url=url,
        ))

    async def _on_spa_navigation(self, params: dict[str, Any]) -> None:
        """Record SPA (single-page app) navigation."""
        if not self._recording:
            return

        url = params.get("url", "")
        if not url:
            return

        self._add_step(PlaybookStep(
            action="navigate",
            timestamp=datetime.now(timezone.utc).isoformat(),
            url=url,
        ))

    async def _on_network_request(self, params: dict[str, Any]) -> None:
        """Record significant network requests (POST/PUT/DELETE/PATCH only).

        Skips GET requests and static assets to reduce noise.
        """
        if not self._recording:
            return

        request = params.get("request", {})
        method = request.get("method", "GET").upper()

        if method not in _RECORDED_METHODS:
            return

        url = request.get("url", "")
        if not url:
            return

        # Skip static assets
        path = url.split("?", 1)[0]
        if any(path.endswith(ext) for ext in _STATIC_EXTENSIONS):
            return

        content_type = ""
        headers = request.get("headers", {})
        for k, v in headers.items():
            if k.lower() == "content-type":
                content_type = v
                break

        self._add_step(PlaybookStep(
            action="request",
            timestamp=datetime.now(timezone.utc).isoformat(),
            url=url,
            method=method,
            content_type=content_type or None,
        ))

    async def _on_network_response(self, params: dict[str, Any]) -> None:
        """Detect file downloads via Content-Disposition header."""
        if not self._recording:
            return

        response = params.get("response", {})
        headers = response.get("headers", {})

        # Check for Content-Disposition to detect downloads
        disposition = ""
        for k, v in headers.items():
            if k.lower() == "content-disposition":
                disposition = v
                break

        if not disposition or "attachment" not in disposition.lower():
            return

        # Extract filename from Content-Disposition
        filename = "unknown"
        if "filename=" in disposition:
            # Handle both filename="foo.csv" and filename=foo.csv
            parts = disposition.split("filename=", 1)[1]
            filename = parts.strip().strip('"').strip("'").split(";")[0].strip()

        url = response.get("url", "")

        self._add_step(PlaybookStep(
            action="download",
            timestamp=datetime.now(timezone.utc).isoformat(),
            url=url,
            value=filename,
        ))

    # ------------------------------------------------------------------
    # Playbook management
    # ------------------------------------------------------------------

    def get_playbook(self, name: str) -> Playbook | None:
        """Get a saved playbook by name."""
        slug = slugify(name)
        return self._playbooks.get(slug)

    def list_playbooks(self) -> list[dict[str, Any]]:
        """Return summary of all saved playbooks."""
        return [
            {
                "name": pb.name,
                "domain": pb.domain,
                "description": pb.description,
                "step_count": len(pb.steps),
                "duration_ms": pb.duration_ms,
                "recorded_at": pb.recorded_at,
            }
            for pb in sorted(
                self._playbooks.values(),
                key=lambda p: p.recorded_at,
                reverse=True,
            )
        ]

    def delete_playbook(self, name: str) -> bool:
        """Delete a saved playbook by name."""
        slug = slugify(name)
        if slug not in self._playbooks:
            return False

        del self._playbooks[slug]

        # Remove file
        path = self._data_dir / f"{slug}.json"
        if path.exists():
            path.unlink()
            logger.info("playbook_recorder: deleted playbook '%s'", slug)

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_step(self, step: PlaybookStep) -> None:
        """Add a step and compute wait_ms from the previous step."""
        now = time.time()
        if self._last_step_time is not None and self._current_steps:
            # Assign wait_ms to the *previous* step (time until this step)
            prev = self._current_steps[-1]
            prev.wait_ms = int((now - self._last_step_time) * 1000)
        self._last_step_time = now
        self._current_steps.append(step)

    def _save_playbook(self, playbook: Playbook) -> None:
        """Persist a single playbook to disk."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._data_dir / f"{playbook.name}.json"
        path.write_text(json.dumps(playbook.to_dict(), indent=2))

    def _save_all(self) -> None:
        """Persist all playbooks to data/playbooks/{name}.json."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        for playbook in self._playbooks.values():
            self._save_playbook(playbook)

    def _load_all(self) -> None:
        """Load existing playbooks from data/playbooks/ on startup."""
        if not self._data_dir.exists():
            return

        for path in self._data_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                pb = Playbook.from_dict(data)
                self._playbooks[pb.name] = pb
                logger.debug("playbook_recorder: loaded playbook '%s'", pb.name)
            except Exception:
                logger.warning(
                    "playbook_recorder: failed to load %s", path, exc_info=True
                )
