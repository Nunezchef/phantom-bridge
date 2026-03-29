"""
browser_bridge_status — A0 tool to check Browser Bridge status.

Reports whether the bridge is running, which pages are open, and
which domains have active sessions.
"""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("browser_bridge")


class BrowserBridgeStatus(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        from usr.plugins.phantom_bridge.bridge import get_bridge

        bridge = get_bridge()

        if not bridge or not bridge.is_running():
            # Check if a profile exists even though bridge is off
            from usr.plugins.phantom_bridge.bridge import create_bridge_from_config

            config = self._load_config()
            tmp_bridge = create_bridge_from_config(config)
            has_profile = tmp_bridge.profile_exists()

            return Response(
                message=(
                    f"Browser bridge is NOT running.\n"
                    f"Existing profile: {'Yes' if has_profile else 'No'}\n"
                    f"Use browser_bridge_open to start it."
                ),
                break_loop=False,
            )

        status = bridge.status()

        # Format pages
        pages_text = ""
        pages = status.get("pages", [])
        if pages:
            lines = []
            for p in pages:
                title = p.get("title", "Untitled")
                url = p.get("url", "")
                lines.append(f"  - {title}: {url}")
            pages_text = "\n".join(lines)
        else:
            pages_text = "  (no pages open)"

        # Format domains
        domains = status.get("authenticated_domains", [])
        domains_text = ", ".join(domains) if domains else "(none)"

        return Response(
            message=(
                f"Browser bridge status:\n"
                f"  Running: {status.get('running', False)}\n"
                f"  Connect URL: {status.get('connect_url', 'N/A')}\n"
                f"  Uptime: {status.get('uptime_seconds', 0)}s\n"
                f"  PID: {status.get('pid', 'N/A')}\n"
                f"  Profile: {status.get('profile_dir', 'N/A')}\n\n"
                f"Open pages ({status.get('page_count', 0)}):\n"
                f"{pages_text}\n\n"
                f"Domains with sessions: {domains_text}"
            ),
            break_loop=False,
        )

    def _load_config(self) -> dict[str, Any]:
        """Load plugin configuration."""
        try:
            from helpers.plugins import get_plugin_config
            return get_plugin_config("browser_bridge", agent=self.agent) or {}
        except ImportError:
            pass

        try:
            import yaml
            from pathlib import Path

            config_path = Path(__file__).resolve().parent.parent / "default_config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
        except ImportError:
            pass

        return {}

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://language {self.agent.agent_name}: Browser Bridge Status",
            content="",
            kvps=self.args,
        )
