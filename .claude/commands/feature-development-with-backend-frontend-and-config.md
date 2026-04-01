---
name: feature-development-with-backend-frontend-and-config
description: Workflow command scaffold for feature-development-with-backend-frontend-and-config in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-backend-frontend-and-config

Use this workflow when working on **feature-development-with-backend-frontend-and-config** in `phantom-bridge`.

## Goal

Implements a new feature that requires coordinated changes across backend logic, API endpoints, configuration files, and frontend UI/store.

## Common Files

- `api/bridge.py`
- `observer/playbook_recorder.py`
- `observer/manager.py`
- `tools/bridge_record.py`
- `tools/bridge_replay.py`
- `plugin.yaml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement backend logic in Python (api/bridge.py, observer/*.py, tools/*.py).
- Update or add API endpoints as needed.
- Modify or extend configuration in plugin.yaml.
- Update or create frontend UI components (webui/*.html, webui/*.js).
- Update the store logic to subscribe to new events or state (webui/phantom-bridge-store.js).

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.