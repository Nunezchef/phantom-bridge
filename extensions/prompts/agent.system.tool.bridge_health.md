### bridge_health:

checks if authenticated browser sessions are still valid
navigates to each domain and verifies the session hasn't expired (not redirected to login)

arguments:
- domain (optional): specific domain to check — if omitted, checks ALL authenticated domains

use when:
- before replaying a playbook — check if the session is still valid
- user says "is my login still active?", "check if I'm still logged in"
- user reports a replay failed due to auth issues
- proactive health check before automated workflows

check a specific domain:
```json
{
  "thoughts": ["Let me verify the Toast session is still valid before running the export"],
  "headline": "Checking Toast session health",
  "tool_name": "bridge_health",
  "tool_args": {
    "domain": "pos.toasttab.com"
  }
}
```

check all domains:
```json
{
  "thoughts": ["Let me check all authenticated sessions before running automated workflows"],
  "headline": "Checking all session health",
  "tool_name": "bridge_health",
  "tool_args": {}
}
```

workflow: health check before replay
1. Check session health for the playbook's domain (bridge_health)
2. If expired — tell the user to re-authenticate via bridge_open
3. If healthy — proceed with bridge_replay
