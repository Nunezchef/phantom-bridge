"""
Phantom Bridge — System Prompt Extension.

Injects bridge awareness into A0's system prompt (ADDITIVE — never replaces
the core prompt). Teaches A0:
- When to suggest the bridge (auth failures, authenticated services)
- What domains are already authenticated
- What playbooks are available for autonomous replay
- Where cookies/sessions are stored
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from helpers.extension import Extension

from agent import LoopData

logger = logging.getLogger("phantom_bridge")

_plugin_dir = Path(__file__).resolve().parent.parent.parent


class BrowserBridgeContext(Extension):
    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ) -> None:
        data_dir = _plugin_dir / "data"
        sections: list[str] = []

        # ----- Core knowledge -----
        sections.append("""
## Phantom Bridge — Browser Authentication & Automation

You have access to a browser bridge plugin that lets the user authenticate
to any web service from their own browser. The user connects via a remote
browser viewer (noVNC) and logs into services — you then inherit those
authenticated sessions for your browser_agent tool.

### When to suggest the bridge
- When your browser_agent cannot access a service because it requires login
- When the user asks you to do something on an authenticated platform
  (Google, NotebookLM, X/Twitter, Threads, Toast, OpenTable, any web app)
- When you detect a login redirect or "please sign in" page
- When cookies/sessions have expired for a previously authenticated domain

**Suggest it like this:** "I need authenticated access to [domain]. Would you
like to open the Phantom Bridge so you can log in? I'll be able to use that
session afterward."

### How it works
1. You call `browser_bridge_open` — this starts the bridge
2. The user opens the remote viewer from A0's sidebar (Phantom Bridge panel)
3. They browse and log in to services using their real browser
4. The observer watches silently — learning auth patterns, site maps, and workflows
5. The user closes the bridge — you now have their authenticated sessions

### Where sessions are stored
- Browser profile (cookies, localStorage): `data/profile/` in the plugin directory
- Auth registry (tracked domains): `data/auth_registry.json`
- Learned sitemaps: `data/sitemaps/` (per-domain URL patterns)
- Recorded playbooks: `data/playbooks/` (replayable workflows)

Sessions persist across container restarts. The profile directory is shared
with your browser_agent tool — any cookies set via the bridge are available
to you immediately.

### Tools
- **browser_bridge_open** — Start the bridge (launches remote viewer)
- **browser_bridge_close** — Stop the bridge (sessions persist)
- **browser_bridge_status** — Check bridge status, open pages, domains
- **bridge_auth** — Which domains are authenticated, session expiry
- **bridge_health** — Test if a domain's session is still valid
- **bridge_sitemap** — Learned URL patterns per domain
- **bridge_record** — Start/stop recording a replayable workflow
- **bridge_replay** — Replay a saved workflow autonomously
""")

        # ----- Live auth state -----
        auth_file = data_dir / "auth_registry.json"
        if auth_file.exists():
            try:
                registry = json.loads(auth_file.read_text())
                if registry:
                    sections.append("### Currently Authenticated Domains")
                    for domain, entry in registry.items():
                        status = "active" if entry.get("authenticated") else "EXPIRED"
                        expires = entry.get("expires_at", "unknown")
                        sections.append(f"- **{domain}** — {status} (expires: {expires})")
                    sections.append("")
                    sections.append(
                        "Use these sessions with browser_agent. If a session shows "
                        "EXPIRED, suggest the user re-authenticate via the bridge."
                    )
                    sections.append("")
            except Exception:
                pass

        # ----- Available playbooks -----
        playbooks_dir = data_dir / "playbooks"
        if playbooks_dir.exists():
            playbook_files = list(playbooks_dir.glob("*.json"))
            if playbook_files:
                sections.append("### Saved Playbooks (replayable workflows)")
                sections.append(
                    "These are workflows the user demonstrated via the bridge. "
                    "You can replay them autonomously using `bridge_replay`."
                )
                for pf in playbook_files[:10]:
                    try:
                        pb = json.loads(pf.read_text())
                        name = pb.get("name", pf.stem)
                        domain = pb.get("domain", "unknown")
                        steps = len(pb.get("steps", []))
                        desc = pb.get("description", "")
                        desc_str = f" — {desc}" if desc else ""
                        sections.append(
                            f"- **{name}** ({domain}, {steps} steps){desc_str}"
                        )
                    except Exception:
                        pass
                sections.append("")
                sections.append(
                    "When the user asks you to repeat a task that matches a saved "
                    "playbook, use `bridge_replay` instead of navigating manually."
                )
                sections.append("")

        # ----- Sitemaps summary -----
        sitemaps_dir = data_dir / "sitemaps"
        if sitemaps_dir.exists():
            sitemap_files = list(sitemaps_dir.glob("*.json"))
            if sitemap_files:
                sections.append("### Learned Site Maps")
                for sf in sitemap_files[:5]:
                    try:
                        sm = json.loads(sf.read_text())
                        domain = sm.get("domain", sf.stem)
                        features = sm.get("features", {})
                        sections.append(
                            f"- **{domain}** — {len(features)} features mapped"
                        )
                    except Exception:
                        pass
                sections.append("")

        system_prompt.append("\n".join(sections))
