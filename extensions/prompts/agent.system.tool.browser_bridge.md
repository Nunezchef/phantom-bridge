### browser_bridge_open:

opens a browser bridge — launches chromium with remote debugging port so the user can connect from their host browser
no arguments required
returns the connection URL for the user to open in their Chrome browser
use this when the user needs to log into a service or you need authenticated browser sessions

usage:
```json
{
  "thoughts": ["I need the user to log into Google/NotebookLM/X so I can use those sessions"],
  "headline": "Opening browser bridge for authentication",
  "tool_name": "browser_bridge_open",
  "tool_args": {}
}
```

### browser_bridge_close:

closes the browser bridge — stops the remote chromium process
sessions and cookies persist in the profile for next time
optional clear_profile argument to wipe all stored data

usage:
```json
{
  "thoughts": ["User is done logging in, closing the bridge"],
  "headline": "Closing browser bridge",
  "tool_name": "browser_bridge_close",
  "tool_args": {
    "clear_profile": "false"
  }
}
```

### browser_bridge_status:

checks if browser bridge is running and what pages/sessions are active
no arguments required
use to verify bridge state before/after operations

usage:
```json
{
  "thoughts": ["Let me check if the bridge is running and what sessions exist"],
  "headline": "Checking browser bridge status",
  "tool_name": "browser_bridge_status",
  "tool_args": {}
}
```
