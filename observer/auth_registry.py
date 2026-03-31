"""
Auth Registry — Watches for authentication events via CDP and maintains
a registry of logged-in domains with session metadata.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .cdp_client import CDPClient

logger = logging.getLogger("phantom_bridge")

# URL path fragments that indicate an authentication endpoint
_AUTH_URL_PATTERNS = frozenset(
    ["/login", "/auth", "/oauth", "/signin", "/session", "/token",
     "/sso", "/callback", "/saml"]
)

# Cookie names commonly used for session/auth tokens
_AUTH_COOKIE_NAMES = frozenset(
    ["session", "sid", "token", "auth", "jwt", "_session",
     "ssid", "SID", "SSID", "sessionid", "session_id",
     "connect.sid", "JSESSIONID", "csrftoken", "access_token",
     "__Secure-", "__Host-"]
)

# Minimum cookie expiry (seconds) to consider it an auth cookie vs tracking
_MIN_AUTH_COOKIE_LIFETIME = 3600  # 1 hour


@dataclass
class AuthEntry:
    """Represents the authentication state for a single domain."""

    domain: str
    authenticated: bool
    detected_at: str  # ISO timestamp
    cookies_count: int
    session_cookie_names: list[str] = field(default_factory=list)
    expires_at: str | None = None  # earliest auth cookie expiry
    login_url: str | None = None  # URL where login was detected
    last_seen: str = ""  # last page load on this domain

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AuthRegistry:
    """Watches for authentication events and maintains a registry of
    logged-in domains."""

    def __init__(self, cdp: CDPClient, data_dir: Path):
        self._cdp = cdp
        self._data_dir = data_dir
        self._registry: dict[str, AuthEntry] = {}
        self._pre_nav_cookies: dict[str, set[str]] = {}  # domain -> cookie names
        self._pending_auth_check: set[str] = set()  # domains flagged for cookie diff
        self._file_path = data_dir / "auth_registry.json"
        # Optional async callable(domain: str, entry: AuthEntry) fired after a new
        # domain is authenticated.  Set via set_auth_callback().
        self._auth_callback = None

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def set_auth_callback(self, callback) -> None:
        """Register an async callable invoked when a domain authenticates.

        Signature: ``async def callback(domain: str, entry: AuthEntry) -> None``

        The callback is fire-and-forget (wrapped in asyncio.create_task) so a
        slow or failing callback never blocks auth detection.
        """
        self._auth_callback = callback

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to CDP events for auth detection and load saved state."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

        await self._cdp.subscribe("Page.loadEventFired", self._on_page_loaded)
        await self._cdp.subscribe("Network.responseReceived", self._on_network_response)
        await self._cdp.subscribe(
            "Page.navigatedWithinDocument", self._on_spa_navigation
        )

        # Take an initial cookie snapshot
        await self._snapshot_cookies()

        logger.info(
            "auth_registry: started (loaded %d entries)", len(self._registry)
        )

    async def stop(self) -> None:
        """Save final state."""
        self._save()
        logger.info("auth_registry: stopped")

    # ------------------------------------------------------------------
    # CDP event handlers
    # ------------------------------------------------------------------

    async def _on_page_loaded(self, params: dict) -> None:
        """After page load: get all cookies, compare with pre-nav state.

        If new auth-looking cookies appeared, a login is detected.
        """
        try:
            cookies = await self._cdp.get_cookies()
        except Exception as exc:
            logger.debug("auth_registry: failed to get cookies on page load: %s", exc)
            return

        # Group cookies by domain
        domains_cookies: dict[str, list[dict]] = {}
        for cookie in cookies:
            domain = cookie.get("domain", "").lstrip(".")
            if domain:
                domains_cookies.setdefault(domain, []).append(cookie)

        # Check domains flagged by network response handler
        for domain in list(self._pending_auth_check):
            if domain in domains_cookies:
                await self._detect_auth_cookies(domain, domains_cookies[domain])
        self._pending_auth_check.clear()

        # Also check all domains for new auth cookies (handles redirects, etc.)
        for domain, domain_cookies in domains_cookies.items():
            await self._detect_auth_cookies(domain, domain_cookies)

        # Update last_seen for domains in registry
        now = datetime.now(timezone.utc).isoformat()
        for domain in domains_cookies:
            if domain in self._registry:
                self._registry[domain].last_seen = now

        # Update pre-nav snapshot for next comparison
        await self._snapshot_cookies()

    async def _on_network_response(self, params: dict) -> None:
        """Watch for POST/PUT to auth-like URLs.

        If detected, flag domain for cookie check on next page load.
        """
        response = params.get("response", {})
        request_url = response.get("url", "")
        status = response.get("status", 0)

        if not request_url:
            return

        # Check request method via requestHeaders or type heuristic
        # CDP Network.responseReceived doesn't always include the method,
        # so we rely on URL pattern matching + status codes
        if status not in (200, 201, 302, 303, 307, 308):
            return

        parsed = urlparse(request_url)
        path_lower = parsed.path.lower()

        is_auth_url = any(pattern in path_lower for pattern in _AUTH_URL_PATTERNS)
        if not is_auth_url:
            return

        domain = parsed.hostname or ""
        if domain:
            self._pending_auth_check.add(domain)
            logger.debug(
                "auth_registry: auth-like response detected: %s (status %d)",
                request_url,
                status,
            )

    async def _on_spa_navigation(self, params: dict) -> None:
        """Handle SPA navigation — treat like a soft page load."""
        url = params.get("url", "")
        if url:
            parsed = urlparse(url)
            domain = parsed.hostname or ""
            if domain and domain in self._registry:
                self._registry[domain].last_seen = (
                    datetime.now(timezone.utc).isoformat()
                )

    # ------------------------------------------------------------------
    # Auth detection
    # ------------------------------------------------------------------

    async def _detect_auth_cookies(
        self, domain: str, cookies: list[dict]
    ) -> None:
        """Compare current cookies with pre-navigation snapshot.

        Auth indicators:
        - New cookies with auth-like names
        - HttpOnly + Secure flags (auth cookies are usually both)
        - Expiry > 1 hour (not just tracking cookies)
        """
        pre_nav = self._pre_nav_cookies.get(domain, set())
        current_names = {c.get("name", "") for c in cookies}
        new_names = current_names - pre_nav

        if not new_names and domain in self._registry:
            # No new cookies but already tracked — nothing to do
            return

        auth_cookie_names: list[str] = []
        earliest_expiry: float | None = None

        for cookie in cookies:
            name = cookie.get("name", "")
            is_new = name in new_names
            is_auth_name = self._is_auth_cookie_name(name)
            is_httponly = cookie.get("httpOnly", False)
            is_secure = cookie.get("secure", False)
            expiry = cookie.get("expires", 0)

            # Score: new + auth-like name is strong signal
            # existing + httponly + secure + long expiry is also a signal
            if is_auth_name and (is_new or (is_httponly and is_secure)):
                # Check expiry if available (-1 means session cookie, which is fine)
                if expiry == -1 or expiry == 0:
                    # Session cookie — valid for auth
                    auth_cookie_names.append(name)
                elif expiry > 0:
                    now_ts = datetime.now(timezone.utc).timestamp()
                    remaining = expiry - now_ts
                    if remaining > _MIN_AUTH_COOKIE_LIFETIME:
                        auth_cookie_names.append(name)
                        if earliest_expiry is None or expiry < earliest_expiry:
                            earliest_expiry = expiry

            elif is_new and is_httponly and is_secure:
                # New HttpOnly+Secure cookie that doesn't match known names
                # — still likely auth
                auth_cookie_names.append(name)
                if expiry > 0:
                    if earliest_expiry is None or expiry < earliest_expiry:
                        earliest_expiry = expiry

        if not auth_cookie_names:
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        expires_iso = (
            datetime.fromtimestamp(earliest_expiry, tz=timezone.utc).isoformat()
            if earliest_expiry
            else None
        )

        # Get login URL if we have one pending
        login_url: str | None = None
        if domain in self._registry:
            login_url = self._registry[domain].login_url

        self._registry[domain] = AuthEntry(
            domain=domain,
            authenticated=True,
            detected_at=now_iso,
            cookies_count=len(cookies),
            session_cookie_names=auth_cookie_names,
            expires_at=expires_iso,
            login_url=login_url,
            last_seen=now_iso,
        )

        logger.info(
            "auth_registry: authentication detected for %s "
            "(cookies: %s)",
            domain,
            ", ".join(auth_cookie_names),
        )

        self._save()

        # Notify listeners (e.g. WS broadcaster) without blocking detection.
        if self._auth_callback is not None:
            asyncio.create_task(
                self._auth_callback(domain, self._registry[domain])
            )

    @staticmethod
    def _is_auth_cookie_name(name: str) -> bool:
        """Check if a cookie name looks like an auth/session cookie."""
        name_lower = name.lower()
        for pattern in _AUTH_COOKIE_NAMES:
            if pattern.lower() in name_lower:
                return True
        return False

    # ------------------------------------------------------------------
    # Cookie snapshots
    # ------------------------------------------------------------------

    async def _snapshot_cookies(self) -> None:
        """Take a snapshot of current cookie names grouped by domain."""
        try:
            cookies = await self._cdp.get_cookies()
        except Exception:
            return

        self._pre_nav_cookies.clear()
        for cookie in cookies:
            domain = cookie.get("domain", "").lstrip(".")
            if domain:
                self._pre_nav_cookies.setdefault(domain, set()).add(
                    cookie.get("name", "")
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_registry(self) -> dict[str, dict]:
        """Return current auth registry as a serializable dict."""
        return {domain: entry.to_dict() for domain, entry in self._registry.items()}

    def get_entry(self, domain: str) -> AuthEntry | None:
        """Return a single auth entry by domain, or None."""
        return self._registry.get(domain)

    def get_all_domains(self) -> list[str]:
        """Return all tracked domain names."""
        return list(self._registry.keys())

    async def check_session_health(self, domain: str) -> dict[str, Any]:
        """Test if a domain's session is still valid.

        Navigates to the domain's last known URL, checks if we get
        redirected to a login page.

        Returns: {"domain": str, "healthy": bool, "reason": str}
        """
        entry = self._registry.get(domain)
        if entry is None:
            return {
                "domain": domain,
                "healthy": False,
                "reason": f"Domain '{domain}' not found in auth registry.",
            }

        # Choose a URL to test: last_seen or construct from domain
        test_url: str | None = None
        if entry.last_seen and entry.last_seen.startswith("http"):
            test_url = entry.last_seen
        else:
            test_url = f"https://{domain}/"

        # Avoid testing a login URL itself — use the domain root instead
        parsed_test = urlparse(test_url)
        if any(
            pattern in (parsed_test.path or "").lower()
            for pattern in _AUTH_URL_PATTERNS
        ):
            test_url = f"{parsed_test.scheme}://{parsed_test.netloc}/"

        # Navigate and watch for redirects to login pages
        final_url: str | None = None
        nav_event = asyncio.Event()

        async def on_frame_navigated(params: dict) -> None:
            nonlocal final_url
            frame = params.get("frame", {})
            # Only track top-level frame
            if frame.get("parentId"):
                return
            final_url = frame.get("url", "")
            nav_event.set()

        await self._cdp.subscribe("Page.frameNavigated", on_frame_navigated)

        try:
            await self._cdp.send(
                "Page.navigate", {"url": test_url}
            )

            # Wait for navigation with a 10-second timeout
            try:
                await asyncio.wait_for(nav_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                return {
                    "domain": domain,
                    "healthy": False,
                    "reason": f"Navigation to {test_url} timed out after 10s.",
                }

            # Check if final URL looks like a login redirect
            if final_url:
                parsed_final = urlparse(final_url)
                final_path = (parsed_final.path or "").lower()
                is_login_redirect = any(
                    pattern in final_path for pattern in _AUTH_URL_PATTERNS
                )

                if is_login_redirect:
                    # Session expired — update registry
                    entry.authenticated = False
                    self._save()
                    return {
                        "domain": domain,
                        "healthy": False,
                        "reason": (
                            f"Redirected to login page: {final_url}. "
                            "Session appears expired."
                        ),
                    }

            # Session is healthy
            return {
                "domain": domain,
                "healthy": True,
                "reason": f"Page loaded normally at {final_url or test_url}.",
            }

        except Exception as exc:
            return {
                "domain": domain,
                "healthy": False,
                "reason": f"Health check failed: {exc}",
            }
        finally:
            # Navigate back to about:blank — don't leave on a random page
            try:
                await self._cdp.send("Page.navigate", {"url": "about:blank"})
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Persist to data/auth_registry.json."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                domain: entry.to_dict() for domain, entry in self._registry.items()
            }
            self._file_path.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            logger.exception("auth_registry: failed to save registry")

    def _load(self) -> None:
        """Load from data/auth_registry.json on startup."""
        if not self._file_path.exists():
            return
        try:
            raw = self._file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            for domain, entry_data in data.items():
                self._registry[domain] = AuthEntry.from_dict(entry_data)
            logger.info(
                "auth_registry: loaded %d entries from disk", len(self._registry)
            )
        except Exception:
            logger.exception("auth_registry: failed to load registry")
