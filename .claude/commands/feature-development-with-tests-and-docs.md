---
name: feature-development-with-tests-and-docs
description: Workflow command scaffold for feature-development-with-tests-and-docs in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-tests-and-docs

Use this workflow when working on **feature-development-with-tests-and-docs** in `phantom-bridge`.

## Goal

Implements a new feature, adds corresponding tests, and updates documentation.

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

- Implement feature logic in core modules (e.g., bridge.py, observer/*.py, api/*.py, etc.)
- Update or add frontend/UI components if needed (e.g., webui/*.js, webui/*.html)
- Add or update automated tests covering the new feature (e.g., tests/test_*.py)
- Update documentation or changelog to reflect the new feature (e.g., README.md, CHANGELOG.md)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.