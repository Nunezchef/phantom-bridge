### browser_bridge_auth:

checks which domains have authenticated sessions in the browser bridge
shows session cookies, expiry times, and when authentication was detected
no arguments required
use this before attempting browser automation to verify you have the needed sessions

usage:
```json
{
  "thoughts": ["I need to check if the user is logged into Google before accessing NotebookLM"],
  "headline": "Checking authenticated sessions",
  "tool_name": "browser_bridge_auth",
  "tool_args": {}
}
```
