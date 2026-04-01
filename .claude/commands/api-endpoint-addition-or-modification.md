---
name: api-endpoint-addition-or-modification
description: Workflow command scaffold for api-endpoint-addition-or-modification in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /api-endpoint-addition-or-modification

Use this workflow when working on **api-endpoint-addition-or-modification** in `phantom-bridge`.

## Goal

Adds or modifies an API endpoint, often with corresponding frontend and config changes.

## Common Files

- `api/bridge.py`
- `plugin.yaml`
- `webui/phantom-bridge-store.js`
- `webui/*.html`
- `tests/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement or update endpoint in api/bridge.py (or related api/*.py)
- Update plugin.yaml if endpoint or settings change
- Update frontend store or UI to consume new endpoint (webui/phantom-bridge-store.js, webui/*.html)
- Write or update tests in tests/ for endpoint behavior

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.