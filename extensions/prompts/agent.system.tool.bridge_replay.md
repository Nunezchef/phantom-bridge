### bridge_replay:

Replays a previously recorded browser workflow using Playwright.
Uses the bridge's persistent browser profile so authenticated sessions are inherited.

This is the core of "show A0 once, it does it forever" — the user demonstrates
a workflow via the bridge, and you can replay it autonomously any time.

arguments:
- name (required): name of the playbook to replay
- dry_run (optional, default "false"): if "true", returns the Playwright script without executing
- skip_health_check (optional, default "false"): skip session health verification

use when:
- user says "do that thing again", "replay the export", "run the task I showed you"
- a saved playbook matches the user's request (check bridge_auth for available playbooks)
- automating a recurring task the user previously demonstrated
- user asks "can you do what I showed you?" or "generate images like I showed you"

IMPORTANT: Before replaying, check bridge_auth to verify the session is still active.
If expired, suggest the user re-authenticate via the bridge first.

replay a recorded workflow:
```json
{
  "thoughts": ["User wants me to generate images on Gemini like they showed me. I have a playbook for this."],
  "headline": "Replaying Gemini image generation workflow",
  "tool_name": "bridge_replay",
  "tool_args": {
    "name": "gemini_image_gen"
  }
}
```

workflow: teach A0 then automate
1. User opens bridge (browser_bridge_open)
2. Tell A0 to start recording: bridge_record start name="task_name"
3. User performs the workflow in the remote viewer
4. Stop recording: bridge_record stop
5. From now on: bridge_replay name="task_name" — A0 does it autonomously
