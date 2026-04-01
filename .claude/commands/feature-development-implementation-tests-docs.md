---
name: feature-development-implementation-tests-docs
description: Workflow command scaffold for feature-development-implementation-tests-docs in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-implementation-tests-docs

Use this workflow when working on **feature-development-implementation-tests-docs** in `phantom-bridge`.

## Goal

Implements a new feature or capability, often with supporting tests and documentation updates.

## Common Files

- `api/bridge.py`
- `observer/*.py`
- `tools/*.py`
- `webui/*.js`
- `webui/*.html`
- `plugin.yaml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement feature logic in backend Python modules (e.g. api/, observer/, tools/)
- Update or add supporting frontend files (webui/..., extensions/webui/...) if needed
- Update or add API endpoints (api/bridge.py, etc.)
- Update plugin.yaml or config if new settings are introduced
- Write or update tests in tests/ for the new feature

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.