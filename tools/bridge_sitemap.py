"""
bridge_sitemap — A0 tool to query learned sitemaps from browser navigation.

Returns per-domain feature maps showing URL patterns, page titles,
and visit frequency observed via the Browser Bridge.
"""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BrowserBridgeSitemap(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        from usr.plugins.phantom_bridge.bridge import get_bridge

        bridge = get_bridge()

        if not bridge or not bridge.is_running():
            return Response(
                message=(
                    "Browser bridge is NOT running.\n"
                    "Start it with browser_bridge_open first."
                ),
                break_loop=False,
            )

        # Access the sitemap learner from the bridge's observer layer
        learner = getattr(bridge, "sitemap_learner", None)
        if learner is None:
            return Response(
                message="Sitemap learner is not available on this bridge instance.",
                break_loop=False,
            )

        domain = self.args.get("domain", "").strip()

        if domain:
            # Single domain detail
            sitemap = learner.get_sitemap(domain)
            if sitemap is None:
                return Response(
                    message=f"No sitemap recorded for domain: {domain}",
                    break_loop=False,
                )
            return Response(
                message=_format_domain(sitemap),
                break_loop=False,
            )

        # All domains summary
        domains = learner.get_all_domains()
        if not domains:
            return Response(
                message=(
                    "No sitemaps learned yet.\n"
                    "Browse some pages with the bridge open and sitemaps "
                    "will be recorded automatically."
                ),
                break_loop=False,
            )

        lines = ["Learned sitemaps:\n"]
        for d in domains:
            sm = learner.get_sitemap(d)
            if sm:
                lines.append(_format_domain(sm))
                lines.append("")

        return Response(
            message="\n".join(lines).strip(),
            break_loop=False,
        )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://map {self.agent.agent_name}: Bridge Sitemap",
            content="",
            kvps=self.args,
        )


def _format_domain(sm: dict) -> str:
    """Format a single domain sitemap into human-readable text."""
    domain = sm["domain"]
    total_visits = sm.get("total_visits", 0)
    features = sm.get("features", {})
    page_count = sum(len(f.get("pages", [])) for f in features.values())

    lines = [f"{domain} ({page_count} pages, {total_visits} visits)"]

    for fname, feat in sorted(features.items()):
        lines.append(f"  {fname}:")
        for page in feat.get("pages", []):
            pattern = page.get("pattern", "?")
            titles = page.get("titles", [])
            title = titles[-1] if titles else ""
            count = page.get("visit_count", 0)
            title_part = f' — "{title}"' if title else ""
            lines.append(f"    {pattern}{title_part} (visited {count}x)")

    return "\n".join(lines)
