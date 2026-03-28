"""
Browser Bridge System Prompt Extension.

Injects tool descriptions for the Browser Bridge into the A0 system prompt
so the agent knows these tools exist and when to use them.
"""

from __future__ import annotations

from typing import Any

try:
    from helpers.extension import Extension
except ImportError:
    from python.helpers.extension import Extension

from agent import LoopData


class BrowserBridgeContext(Extension):
    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ) -> None:
        context_parts = [
            "",
            "## Browser Bridge",
            "You can open a browser bridge that lets the user connect to the "
            "container's Chromium browser from their host machine via Chrome "
            "DevTools Protocol. This lets them log into any service (Google, "
            "NotebookLM, X/Twitter, Threads, etc.) and you inherit those "
            "authenticated sessions for your browser_agent tool.",
            "",
            "Available tools:",
            "- **browser_bridge_open** — Start the bridge. Returns a URL "
            "  (http://localhost:9222) the user opens in their host Chrome.",
            "- **browser_bridge_close** — Stop the bridge. Sessions persist "
            "  in the profile. Optional: clear_profile='true' to wipe all data.",
            "- **browser_bridge_status** — Check if bridge is running, list "
            "  open pages and authenticated domains.",
            "",
            "Workflow:",
            "1. User asks to log into a service or you need an authenticated session.",
            "2. Call browser_bridge_open. Tell the user the connect URL.",
            "3. User opens the URL, logs into their services in the remote browser.",
            "4. User confirms they're done. Call browser_bridge_close.",
            "5. Now browser_agent can use those sessions — cookies and localStorage persist.",
            "",
            "Key points:",
            "- The bridge uses a persistent profile, so sessions survive restarts.",
            "- This replaces cookie export/import which breaks due to fingerprint mismatch.",
            "- The user MUST have port 9222 mapped in docker-compose to use this.",
        ]

        system_prompt.append("\n".join(context_parts))
