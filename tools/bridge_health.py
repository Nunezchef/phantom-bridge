"""
bridge_health — A0 tool to check session health for authenticated domains.

Navigates to each domain's last known URL and checks if the session
is still valid (not redirected to a login page).
"""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeHealth(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        domain = self.args.get("domain", "").strip()

        manager = self._get_observer_manager()
        if manager is None:
            return Response(
                message=(
                    "Browser bridge is not running or observer layers are unavailable.\n"
                    "Start the bridge first with bridge_open."
                ),
                break_loop=False,
            )

        auth = manager.auth

        if domain:
            # Check a single domain
            result = await auth.check_session_health(domain)
            return self._format_single(result)

        # Check all authenticated domains
        all_domains = auth.get_all_domains()
        if not all_domains:
            return Response(
                message=(
                    "No authenticated domains in the registry.\n"
                    "The user needs to log into services via the browser bridge first."
                ),
                break_loop=False,
            )

        results: list[dict[str, Any]] = []
        for d in all_domains:
            result = await auth.check_session_health(d)
            results.append(result)

        return self._format_all(results)

    def _format_single(self, result: dict[str, Any]) -> Response:
        """Format a single health check result."""
        status = "HEALTHY" if result["healthy"] else "EXPIRED"
        msg = (
            f"Session health for {result['domain']}: {status}\n"
            f"Reason: {result['reason']}"
        )
        return Response(message=msg, break_loop=False)

    def _format_all(self, results: list[dict[str, Any]]) -> Response:
        """Format health check results for all domains."""
        lines = ["Session health check results:\n"]
        healthy_count = 0
        expired_count = 0

        for r in results:
            status = "HEALTHY" if r["healthy"] else "EXPIRED"
            if r["healthy"]:
                healthy_count += 1
            else:
                expired_count += 1
            lines.append(f"  {r['domain']}: {status}")
            lines.append(f"    {r['reason']}")
            lines.append("")

        lines.append(
            f"Summary: {healthy_count} healthy, {expired_count} expired "
            f"(out of {len(results)} domains)"
        )

        return Response(message="\n".join(lines), break_loop=False)

    def _get_observer_manager(self) -> Any | None:
        """Get the ObserverManager instance from the bridge."""
        try:
            from plugins.browser_bridge.bridge import get_bridge

            bridge = get_bridge()
            if bridge and bridge.is_running():
                return getattr(bridge, "_observer_manager", None)
        except ImportError:
            pass

        try:
            ctx = self.agent.context
            if hasattr(ctx, "observer_manager"):
                return ctx.observer_manager
        except Exception:
            pass

        return None

    def get_log_object(self):
        domain = self.args.get("domain", "all domains")
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://health_and_safety {self.agent.agent_name}: Session Health Check ({domain})",
            content="",
            kvps=self.args,
        )
