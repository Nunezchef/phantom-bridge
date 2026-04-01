---
name: bugfix-with-targeted-tests
description: Workflow command scaffold for bugfix-with-targeted-tests in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /bugfix-with-targeted-tests

Use this workflow when working on **bugfix-with-targeted-tests** in `phantom-bridge`.

## Goal

Fixes a specific bug and adds or updates tests to verify the fix.

## Common Files

- `bridge.py`
- `observer/*.py`
- `api/*.py`
- `webui/*.js`
- `webui/*.html`
- `tests/test_*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify and fix the bug in the relevant source file(s)
- Add or update a targeted test in tests/test_*.py to reproduce and verify the fix
- Optionally update documentation or changelog if the fix is user-facing

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.