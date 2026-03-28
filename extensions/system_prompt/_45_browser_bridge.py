"""
Browser Bridge System Prompt Extension.

Injects tool descriptions and live observer state (authenticated domains,
learned sitemaps, available playbooks) into the A0 system prompt.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from helpers.extension import Extension

from agent import LoopData

logger = logging.getLogger("phantom_bridge")


class BrowserBridgeContext(Extension):
    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ) -> None:
        context_parts = [
            "",
            "## Phantom Bridge (Browser Bridge + Observer)",
            "You can open a browser bridge that lets the user connect to the "
            "container's Chromium browser from their host machine via Chrome "
            "DevTools Protocol. This lets them log into any service (Google, "
            "Toast, OpenTable, X/Twitter, etc.) and you inherit those "
            "authenticated sessions for your browser_agent tool.",
            "",
            "While the bridge is open, observer layers automatically watch "
            "the user's navigation and learn:",
            "- **Auth Registry** — which domains are authenticated, session expiry",
            "- **Sitemap Learner** — URL patterns and feature maps per domain",
            "- **Playbook Recorder** — replayable navigation sequences",
            "",
            "### Tools",
            "- **browser_bridge_open** — Start the bridge (returns connect URL)",
            "- **browser_bridge_close** — Stop the bridge (sessions persist)",
            "- **browser_bridge_status** — Bridge status, open pages, domains",
            "- **bridge_auth** — Which domains are authenticated and when sessions expire",
            "- **bridge_sitemap** — Learned URL patterns and feature maps",
            "- **bridge_record** — Start/stop recording a playbook (start, stop, list, delete)",
            "- **bridge_replay** — Replay a saved playbook (or dry_run to preview script)",
            "",
        ]

        # Inject live state from observer data files
        plugin_dir = Path(__file__).resolve().parent.parent.parent
        data_dir = plugin_dir / "data"

        # Auth registry
        auth_file = data_dir / "auth_registry.json"
        if auth_file.exists():
            try:
                registry = json.loads(auth_file.read_text())
                if registry:
                    context_parts.append("### Authenticated Domains")
                    for domain, entry in registry.items():
                        status = "active" if entry.get("authenticated") else "expired"
                        expires = entry.get("expires_at", "unknown")
                        context_parts.append(f"- **{domain}** — {status} (expires: {expires})")
                    context_parts.append("")
            except Exception:
                pass

        # Sitemaps summary
        sitemaps_dir = data_dir / "sitemaps"
        if sitemaps_dir.exists():
            sitemap_files = list(sitemaps_dir.glob("*.json"))
            if sitemap_files:
                context_parts.append("### Learned Sitemaps")
                for sf in sitemap_files[:5]:  # limit to 5 domains
                    try:
                        sm = json.loads(sf.read_text())
                        domain = sm.get("domain", sf.stem)
                        features = sm.get("features", {})
                        context_parts.append(
                            f"- **{domain}** — {len(features)} features mapped"
                        )
                    except Exception:
                        pass
                context_parts.append("")

        # Playbooks summary
        playbooks_dir = data_dir / "playbooks"
        if playbooks_dir.exists():
            playbook_files = list(playbooks_dir.glob("*.json"))
            if playbook_files:
                context_parts.append("### Available Playbooks")
                for pf in playbook_files[:10]:
                    try:
                        pb = json.loads(pf.read_text())
                        name = pb.get("name", pf.stem)
                        domain = pb.get("domain", "unknown")
                        steps = len(pb.get("steps", []))
                        context_parts.append(
                            f"- **{name}** ({domain}) — {steps} steps"
                        )
                    except Exception:
                        pass
                context_parts.append("")

        system_prompt.append("\n".join(context_parts))
