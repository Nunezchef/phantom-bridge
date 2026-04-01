"""bridge_session_health — A0 tool to check per-domain session health."""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeSessionHealth(Tool):
    async def execute(self, **kwargs: Any) -> Response:
        from usr.plugins.phantom_bridge.bridge import get_bridge

        bridge = get_bridge()
        if not bridge or not bridge.is_running():
            return Response(
                message=(
                    "Browser bridge is NOT running.\n"
                    "No session health data available.\n"
                    "Use browser_bridge_open to start the bridge first."
                ),
                break_loop=False,
            )

        om = getattr(bridge, "_observer_manager", None)
        if om is None:
            return Response(
                message="Observer manager not available — bridge may have started without observers.",
                break_loop=False,
            )

        auth = getattr(om, "auth", None)
        if auth is None:
            return Response(
                message="Auth registry not available.",
                break_loop=False,
            )

        expiry = auth.check_expired_sessions()
        registry = auth.get_registry()

        cdp = getattr(om, "_cdp", None)
        cdp_healthy = cdp.healthy if cdp else False

        lines = ["Session Health Report\n"]
        lines.append(
            f"CDP Connection: {'Healthy' if cdp_healthy else 'Disconnected'}\n"
        )

        if expiry["expired"]:
            lines.append(f"EXPIRED sessions: {', '.join(expiry['expired'])}\n")
        if expiry["expiring_soon"]:
            lines.append(f"Expiring within 24h: {', '.join(expiry['expiring_soon'])}\n")

        lines.append("\nPer-domain details:")
        for domain, entry in sorted(registry.items()):
            is_expired = domain in expiry["expired"]
            is_expiring = domain in expiry["expiring_soon"]
            status = (
                "EXPIRED"
                if is_expired
                else ("Expiring soon" if is_expiring else "Active")
            )
            cookies = entry.get("session_cookie_count", 0)
            expires = entry.get("expires_at", "session-based")
            lines.append(f"  {domain}: {status} — {cookies} cookies, expires {expires}")

        if not registry:
            lines.append("  No authenticated domains.")

        return Response(message="\n".join(lines), break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://heart_pulse {self.agent.agent_name}: Session Health",
            content="",
            kvps=self.args,
        )
