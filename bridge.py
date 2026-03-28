"""
Browser Bridge — Core bridge logic.

Launches a persistent Chromium instance with --remote-debugging-port so the
host machine can connect via Chrome DevTools Protocol.  The browser profile
is stored in the plugin's data directory and is reused across bridge sessions
AND by A0's browser_agent tool (when patched via the extension).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("browser_bridge")

# ---------------------------------------------------------------------------
# Singleton state — one bridge per container
# ---------------------------------------------------------------------------

_bridge: BrowserBridge | None = None


def get_bridge() -> BrowserBridge | None:
    """Return the current bridge instance (if any)."""
    return _bridge


class BrowserBridge:
    """Manages a Chromium process with remote debugging enabled."""

    def __init__(
        self,
        profile_dir: str | Path,
        remote_debug_port: int = 9222,
        bind_address: str = "0.0.0.0",
        headless: bool = False,
        window_width: int = 1280,
        window_height: int = 900,
        default_url: str = "about:blank",
        executable_path: str | None = None,
    ):
        self.profile_dir = Path(profile_dir)
        self.remote_debug_port = remote_debug_port
        self.bind_address = bind_address
        self.headless = headless
        self.window_width = window_width
        self.window_height = window_height
        self.default_url = default_url
        self.executable_path = executable_path

        self._process: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._started_at: float | None = None
        self._observer_manager = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> dict[str, Any]:
        """Launch Chromium with remote debugging.  Returns connection info."""
        global _bridge

        if self.is_running():
            return self.status()

        # Ensure profile directory exists
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        # Resolve Chromium binary
        chrome_bin = self._resolve_chromium()

        args = [
            str(chrome_bin),
            f"--remote-debugging-port={self.remote_debug_port}",
            f"--remote-debugging-address={self.bind_address}",
            f"--user-data-dir={self.profile_dir}",
            f"--window-size={self.window_width},{self.window_height}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        if self.headless:
            args.append("--headless=new")

        # Open default page
        args.append(self.default_url)

        logger.info(
            "browser_bridge: launching Chromium on port %d (profile: %s)",
            self.remote_debug_port,
            self.profile_dir,
        )

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Chromium binary not found at {chrome_bin}. "
                "Make sure Playwright is installed: playwright install chromium"
            )

        self._started_at = time.time()
        _bridge = self

        # Wait for the debug port to be ready
        await self._wait_for_devtools()

        # Start observer layers (auth registry, sitemap learner, playbook recorder)
        try:
            from observer.manager import ObserverManager

            data_dir = self.profile_dir.parent  # data/ directory (sibling to profile/)
            self._observer_manager = ObserverManager(
                port=self.remote_debug_port,
                data_dir=data_dir,
            )
            await self._observer_manager.start()
            logger.info("browser_bridge: observer layers started")
        except Exception as e:
            logger.warning("browser_bridge: observer layers failed to start: %s", e)
            self._observer_manager = None

        return self.status()

    async def stop(self) -> dict[str, Any]:
        """Stop the bridge Chromium process."""
        global _bridge

        if not self.is_running():
            return {"running": False, "message": "Bridge was not running."}

        # Stop observer layers first
        if self._observer_manager:
            try:
                await self._observer_manager.stop()
                logger.info("browser_bridge: observer layers stopped")
            except Exception as e:
                logger.warning("browser_bridge: error stopping observers: %s", e)
            self._observer_manager = None

        pid = self._process.pid if self._process else None
        try:
            if self._process:
                # Kill the entire process group
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                else:
                    self._process.terminate()
                self._process.wait(timeout=5)
        except Exception as e:
            logger.warning("browser_bridge: error stopping process: %s", e)
            if self._process:
                self._process.kill()
        finally:
            self._process = None
            self._started_at = None
            _bridge = None

        return {"running": False, "message": f"Bridge stopped (pid {pid})."}

    def is_running(self) -> bool:
        """Check if the Chromium process is still alive."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def status(self) -> dict[str, Any]:
        """Return current bridge status."""
        running = self.is_running()
        info: dict[str, Any] = {
            "running": running,
            "port": self.remote_debug_port,
            "profile_dir": str(self.profile_dir),
        }

        if running and self._started_at:
            info["uptime_seconds"] = int(time.time() - self._started_at)
            info["connect_url"] = f"http://localhost:{self.remote_debug_port}"
            info["pid"] = self._process.pid if self._process else None

        # List active pages via DevTools JSON endpoint
        if running:
            try:
                pages = self._get_devtools_pages()
                info["pages"] = pages
                info["page_count"] = len(pages)

                # Extract domains with active sessions
                domains = set()
                for page in pages:
                    url = page.get("url", "")
                    if url and "://" in url:
                        domain = url.split("://", 1)[1].split("/", 1)[0]
                        if domain and domain not in ("blank", "newtab"):
                            domains.add(domain)
                info["authenticated_domains"] = sorted(domains)
            except Exception:
                info["pages"] = []
                info["page_count"] = 0
                info["authenticated_domains"] = []

        return info

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def get_profile_dir(self) -> Path:
        """Return the persistent profile directory path."""
        return self.profile_dir

    def profile_exists(self) -> bool:
        """Check if a browser profile already exists."""
        return self.profile_dir.exists() and any(self.profile_dir.iterdir())

    def clear_profile(self) -> None:
        """Delete the browser profile (all cookies, sessions, localStorage)."""
        if self.is_running():
            raise RuntimeError("Cannot clear profile while bridge is running. Stop the bridge first.")
        if self.profile_dir.exists():
            shutil.rmtree(self.profile_dir)
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            logger.info("browser_bridge: profile cleared at %s", self.profile_dir)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_chromium(self) -> str | Path:
        """Find a usable Chromium binary."""
        if self.executable_path:
            return self.executable_path

        # Try A0's Playwright-installed Chromium first
        try:
            from helpers.playwright import get_playwright_binary, ensure_playwright_binary

            binary = get_playwright_binary()
            if binary:
                # The headless_shell binary can't do headed mode with DevTools.
                # We need the full chromium binary instead.
                full_chrome = self._find_full_chromium_from_playwright(binary)
                if full_chrome:
                    return full_chrome
                # Fall back to headless shell if that's all we have
                return str(binary)

            # Install if not present
            binary = ensure_playwright_binary()
            full_chrome = self._find_full_chromium_from_playwright(binary)
            if full_chrome:
                return full_chrome
            return str(binary)
        except ImportError:
            pass

        # Try system Chromium / Chrome
        for name in [
            "chromium-browser",
            "chromium",
            "google-chrome",
            "google-chrome-stable",
        ]:
            path = shutil.which(name)
            if path:
                return path

        raise RuntimeError(
            "No Chromium binary found. Install via: playwright install chromium"
        )

    def _find_full_chromium_from_playwright(self, headless_binary: str | Path) -> str | None:
        """Given a headless_shell binary path, find the full Chromium binary
        in the same Playwright cache (needed for headed + DevTools mode)."""
        pw_path = Path(headless_binary)
        # Walk up to find the playwright cache root
        # Typical: .../chromium_headless_shell-XXXX/chrome-linux/headless_shell
        # Full:    .../chromium-XXXX/chrome-linux/chrome
        cache_root = pw_path.parent.parent.parent
        if not cache_root.exists():
            return None

        for pattern in (
            "chromium-*/chrome-*/chrome",
            "chromium-*/chrome-*/chromium",
            "chromium-*/chrome-*/Chromium.app/Contents/MacOS/Chromium",
            "chromium-*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        ):
            match = next(cache_root.glob(pattern), None)
            if match and match.exists():
                return str(match)
        return None

    def _get_devtools_pages(self) -> list[dict[str, Any]]:
        """Query the DevTools HTTP JSON API for open pages."""
        import urllib.request

        url = f"http://127.0.0.1:{self.remote_debug_port}/json"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                data = json.loads(resp.read().decode())
                return [
                    {
                        "title": p.get("title", ""),
                        "url": p.get("url", ""),
                        "type": p.get("type", ""),
                    }
                    for p in data
                    if p.get("type") == "page"
                ]
        except Exception:
            return []

    async def _wait_for_devtools(self, timeout: float = 10.0) -> None:
        """Poll the DevTools endpoint until it responds or timeout."""
        import urllib.request

        url = f"http://127.0.0.1:{self.remote_debug_port}/json/version"
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        logger.info("browser_bridge: DevTools ready on port %d", self.remote_debug_port)
                        return
            except Exception:
                pass
            await asyncio.sleep(0.3)

        logger.warning(
            "browser_bridge: DevTools did not respond within %.0fs (may still be starting)",
            timeout,
        )


# ---------------------------------------------------------------------------
# Factory — creates a BrowserBridge from plugin config
# ---------------------------------------------------------------------------

def create_bridge_from_config(config: dict[str, Any] | None = None) -> BrowserBridge:
    """Create a BrowserBridge instance from A0 plugin config dict."""
    config = config or {}

    plugin_dir = Path(__file__).resolve().parent
    profile_dir = plugin_dir / config.get("profile_dir", "data/profile")

    return BrowserBridge(
        profile_dir=profile_dir,
        remote_debug_port=config.get("remote_debug_port", 9222),
        bind_address=config.get("bind_address", "0.0.0.0"),
        headless=config.get("headless", False),
        window_width=config.get("window_width", 1280),
        window_height=config.get("window_height", 900),
        default_url=config.get("default_url", "about:blank"),
        executable_path=config.get("executable_path"),
    )
