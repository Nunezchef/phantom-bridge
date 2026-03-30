"""
bridge_decrypt_cookies — A0 tool to decrypt stored cookies on demand.

Returns plaintext cookie values for a specific domain so A0 can use them
in HTTP requests. Values are returned in memory only — never written
unencrypted to disk.
"""

from __future__ import annotations

import logging
from typing import Any

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeDecryptCookies(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        domain = kwargs.get("domain", "").strip()

        if not domain:
            # List available domains
            from usr.plugins.phantom_bridge.cookie_crypt import list_cookie_domains
            domains = list_cookie_domains()
            if not domains:
                return Response(
                    message=(
                        "No encrypted cookies stored.\n"
                        "Use browser_bridge_open to start the bridge, "
                        "log into services, then cookies will be exported automatically."
                    ),
                    break_loop=False,
                )
            return Response(
                message=(
                    "Available cookie domains:\n"
                    + "\n".join(f"  - {d}" for d in domains)
                    + "\n\nCall this tool with domain='<domain>' to decrypt cookies."
                ),
                break_loop=False,
            )

        from usr.plugins.phantom_bridge.cookie_crypt import load_domain_cookies

        cookies = load_domain_cookies(domain, decrypt=True)
        if not cookies:
            return Response(
                message=f"No cookies stored for domain '{domain}'.",
                break_loop=False,
            )

        # Format as a usable cookie header + individual cookie details
        cookie_header = "; ".join(
            f"{c['name']}={c.get('value', '')}" for c in cookies
        )

        lines = [
            f"Decrypted {len(cookies)} cookies for {domain}:\n",
            f"Cookie header (for HTTP requests):\n  {cookie_header}\n",
            "Individual cookies:",
        ]
        for c in cookies:
            secure = "Secure" if c.get("secure") else ""
            httponly = "HttpOnly" if c.get("httpOnly") else ""
            flags = " ".join(filter(None, [secure, httponly]))
            lines.append(
                f"  {c['name']}={c.get('value', '')}"
                f"  (path={c.get('path', '/')}"
                f"{', ' + flags if flags else ''})"
            )

        return Response(
            message="\n".join(lines),
            break_loop=False,
        )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://cookie {self.agent.agent_name}: Decrypt Cookies",
            content="",
            kvps=self.args,
        )
