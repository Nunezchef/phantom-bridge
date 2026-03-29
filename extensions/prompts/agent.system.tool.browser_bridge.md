### browser_bridge_open:

Opens the Phantom Bridge — launches the container's Chromium with a remote viewer (noVNC) so the user can connect and log into web services.
No arguments required.
Returns the viewer URL. The user opens it from A0's sidebar (Phantom Bridge panel) or directly.
Use this when you need authenticated browser sessions — when your browser_agent hits a login page, gets redirected to sign-in, or the user asks you to interact with an authenticated service.

IMPORTANT: Proactively suggest opening the bridge when you detect authentication is needed. Don't just fail silently — tell the user you need them to log in via the bridge.

usage:
```json
{
  "thoughts": ["I need the user to log into Google/NotebookLM/X so I can use those sessions. I'll open the bridge for them."],
  "headline": "Opening browser bridge for authentication",
  "tool_name": "browser_bridge_open",
  "tool_args": {}
}
```

### browser_bridge_close:

Closes the browser bridge — stops the remote viewer.
Sessions and cookies PERSIST in the profile for next time — they are not deleted.
Optional clear_profile argument to wipe all stored sessions.

usage:
```json
{
  "thoughts": ["User is done logging in, closing the bridge. Sessions will persist."],
  "headline": "Closing browser bridge",
  "tool_name": "browser_bridge_close",
  "tool_args": {
    "clear_profile": "false"
  }
}
```

### browser_bridge_status:

Checks if the bridge is running, which pages are open, and which domains have active sessions.
Use to verify auth state before attempting authenticated browser operations.

usage:
```json
{
  "thoughts": ["Let me check if the bridge is running and what sessions exist before trying to access Toast POS"],
  "headline": "Checking bridge status and active sessions",
  "tool_name": "browser_bridge_status",
  "tool_args": {}
}
```
