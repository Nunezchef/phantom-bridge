"""
browser_bridge_close — A0 tool to stop the Browser Bridge.

Shuts down the bridge Chromium process.  The browser profile is preserved
so sessions survive for next time.
"""

from __future__ import annotations

import logging
from typing import Any

from python.helpers.tool import Tool, Response

logger = logging.getLogger("browser_bridge")


class BrowserBridgeClose(Tool):

    async def execute(self, clear_profile: str = "", **kwargs: Any) -> Response:
        from plugins.browser_bridge.bridge import get_bridge

        bridge = get_bridge()

        if not bridge or not bridge.is_running():
            return Response(
                message="Browser bridge is not running. Nothing to stop.",
                break_loop=False,
            )

        result = await bridge.stop()

        # Optionally clear the profile
        should_clear = str(clear_profile).lower().strip() == "true"
        if should_clear and bridge:
            bridge.clear_profile()
            result["message"] += " Profile data cleared."

        return Response(
            message=(
                f"{result.get('message', 'Bridge stopped.')}\n"
                f"Browser profile preserved at: {bridge.profile_dir}\n"
                f"Authenticated sessions will be available next time the bridge starts."
            ),
            break_loop=False,
        )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://language {self.agent.agent_name}: Closing Browser Bridge",
            content="",
            kvps=self.args,
        )
