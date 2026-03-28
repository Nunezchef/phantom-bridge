### bridge_replay:

replays a previously recorded browser playbook using Playwright
uses the bridge's persistent browser profile so authenticated sessions are inherited automatically

arguments:
- name (required): name of the playbook to replay
- dry_run (optional, default "false"): if "true", returns the Playwright script without executing

use when:
- user says "do that thing again", "replay the export", "run the daily sales export"
- user wants to re-execute a previously recorded workflow
- user asks "can you do what I showed you?"
- automating a recurring task that was previously recorded with bridge_record

replay a playbook:
```json
{
  "thoughts": ["User wants me to run the daily sales export they recorded earlier"],
  "headline": "Replaying daily sales export",
  "tool_name": "bridge_replay",
  "tool_args": {
    "name": "daily_sales_export"
  }
}
```

preview the script without executing:
```json
{
  "thoughts": ["User wants to review the replay script before running it"],
  "headline": "Generating replay script (dry run)",
  "tool_name": "bridge_replay",
  "tool_args": {
    "name": "daily_sales_export",
    "dry_run": "true"
  }
}
```

workflow: record then replay
1. User opens browser bridge (bridge_open)
2. User navigates through workflow while recording (bridge_record start)
3. User finishes, stop recording (bridge_record stop)
4. Later: replay the workflow (bridge_replay)
