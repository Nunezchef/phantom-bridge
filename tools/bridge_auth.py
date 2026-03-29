"""
browser_bridge_auth — A0 tool to check authentication registry.

Reports which domains have authenticated sessions, cookie expiry,
and session health from the CDP observer layer.
"""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BrowserBridgeAuth(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        from usr.plugins.phantom_bridge.bridge import get_bridge

        bridge = get_bridge()

        if not bridge or not bridge.is_running():
            return Response(
                message=(
                    "Browser bridge is NOT running.\n"
                    "No authentication data available.\n"
                    "Use browser_bridge_open to start the bridge first."
                ),
                break_loop=False,
            )

        # Try to get the observer manager's auth registry
        try:
            from usr.plugins.phantom_bridge.observer import ObserverManager

            # Check if an observer manager is attached to the bridge
            manager = getattr(bridge, "_observer_manager", None)

            if manager is None:
                # Observer not started — fall back to registry file
                return self._read_registry_from_file()

            registry = manager.auth.get_registry()

            if not registry:
                return Response(
                    message=(
                        "Auth registry is empty.\n"
                        "No authenticated sessions detected yet.\n"
                        "The user needs to log into services via the browser bridge."
                    ),
                    break_loop=False,
                )

            return self._format_registry(registry)

        except ImportError:
            return self._read_registry_from_file()

    def _format_registry(self, registry: dict[str, dict]) -> Response:
        """Format the auth registry into a human-readable response."""
        lines = ["Authenticated domains:\n"]

        for domain, entry in sorted(registry.items()):
            auth_status = "Authenticated" if entry.get("authenticated") else "Unknown"
            cookies = entry.get("session_cookie_names", [])
            expires = entry.get("expires_at", "session-based")
            login_url = entry.get("login_url", "N/A")
            last_seen = entry.get("last_seen", "N/A")
            detected = entry.get("detected_at", "N/A")

            lines.append(f"  {domain}:")
            lines.append(f"    Status: {auth_status}")
            lines.append(f"    Session cookies: {', '.join(cookies) if cookies else 'none'}")
            lines.append(f"    Expires: {expires or 'session-based'}")
            lines.append(f"    Login URL: {login_url or 'N/A'}")
            lines.append(f"    Detected: {detected}")
            lines.append(f"    Last seen: {last_seen}")
            lines.append("")

        return Response(
            message="\n".join(lines),
            break_loop=False,
        )

    def _read_registry_from_file(self) -> Response:
        """Fall back to reading the persisted auth_registry.json."""
        import json
        from pathlib import Path

        registry_path = (
            Path(__file__).resolve().parent.parent / "data" / "auth_registry.json"
        )

        if not registry_path.exists():
            return Response(
                message=(
                    "Auth registry file not found.\n"
                    "No authentication data available.\n"
                    "The observer layer may not have been started yet."
                ),
                break_loop=False,
            )

        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            if not data:
                return Response(
                    message="Auth registry is empty — no authenticated sessions detected.",
                    break_loop=False,
                )
            return self._format_registry(data)
        except Exception as exc:
            return Response(
                message=f"Failed to read auth registry: {exc}",
                break_loop=False,
            )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://security {self.agent.agent_name}: Browser Auth Registry",
            content="",
            kvps=self.args,
        )
