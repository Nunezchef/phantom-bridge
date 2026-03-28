### bridge_record:

records user browser actions as a replayable playbook
watches navigation, form submissions, and downloads via Chrome DevTools Protocol — pure observation, never interferes with browsing

arguments:
- action (required): "start", "stop", "list", or "delete"
- name (required for start/delete): playbook name (will be slugified)
- description (optional, used on stop): description of what the workflow does

use when:
- user says "record this", "watch what I do", "learn this workflow", "save this process"
- user is about to walk through a multi-step browser workflow they want to automate
- you need to capture a repeatable process (daily export, report generation, etc.)

start recording:
```json
{
  "thoughts": ["The user wants me to learn their daily sales export workflow"],
  "headline": "Recording browser workflow",
  "tool_name": "bridge_record",
  "tool_args": {
    "action": "start",
    "name": "daily_sales_export"
  }
}
```

stop recording:
```json
{
  "thoughts": ["User finished the workflow, saving the playbook"],
  "headline": "Saving recorded workflow",
  "tool_name": "bridge_record",
  "tool_args": {
    "action": "stop",
    "description": "Export daily sales report from POS dashboard"
  }
}
```

list saved playbooks:
```json
{
  "thoughts": ["Let me check what workflows we have recorded"],
  "headline": "Listing saved playbooks",
  "tool_name": "bridge_record",
  "tool_args": {
    "action": "list"
  }
}
```

delete a playbook:
```json
{
  "thoughts": ["User wants to remove an outdated playbook"],
  "headline": "Deleting playbook",
  "tool_name": "bridge_record",
  "tool_args": {
    "action": "delete",
    "name": "old_workflow"
  }
}
```
