---
name: bugfix-with-associated-test-or-integration-update
description: Workflow command scaffold for bugfix-with-associated-test-or-integration-update in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /bugfix-with-associated-test-or-integration-update

Use this workflow when working on **bugfix-with-associated-test-or-integration-update** in `phantom-bridge`.

## Goal

Fixes a bug in backend or frontend code and adds or updates a corresponding test to verify the fix.

## Common Files

- `observer/manager.py`
- `observer/playbook_recorder.py`
- `observer/sitemap_learner.py`
- `tools/bridge_record.py`
- `tools/bridge_replay.py`
- `webui/phantom-bridge-store.js`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify and fix the bug in the relevant Python or JS file.
- Update or add a test in tests/ to cover the fixed behavior.
- Sometimes update related logic in webui or tools to ensure integration.
- Commit both the fix and the test together.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.