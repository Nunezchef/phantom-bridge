---
name: feature-development-with-tests-and-docs
description: Workflow command scaffold for feature-development-with-tests-and-docs in phantom-bridge.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-tests-and-docs

Use this workflow when working on **feature-development-with-tests-and-docs** in `phantom-bridge`.

## Goal

Implements a new feature or major compatibility layer, accompanied by targeted tests and sometimes documentation updates.

## Common Files

- `api/bridge.py`
- `bridge.py`
- `observer/manager.py`
- `observer/playbook_recorder.py`
- `observer/sitemap_learner.py`
- `tools/bridge_record.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement feature logic (often in multiple core files).
- Update or add related tests in tests/ directory.
- Update documentation or prompts if relevant (README.md, CHANGELOG.md, or prompt files).

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.