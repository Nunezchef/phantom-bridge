---
name: phantom-bridge-conventions
description: Development conventions and patterns for phantom-bridge. Python project with conventional commits.
---

# Phantom Bridge Conventions

> Generated from [Nunezchef/phantom-bridge](https://github.com/Nunezchef/phantom-bridge) on 2026-04-01

## Overview

This skill teaches Claude the development patterns and conventions used in phantom-bridge.

## Tech Stack

- **Primary Language**: Python
- **Architecture**: hybrid module organization
- **Test Location**: separate

## When to Use This Skill

Activate this skill when:
- Making changes to this repository
- Adding new features following established patterns
- Writing tests that match project conventions
- Creating commits with proper message format

## Commit Conventions

Follow these commit message conventions based on 67 analyzed commits.

### Commit Style: Conventional Commits

### Prefixes Used

- `fix`
- `feat`
- `docs`
- `chore`

### Message Guidelines

- Average message length: ~57 characters
- Keep first line concise and descriptive
- Use imperative mood ("Add feature" not "Added feature")


*Commit message example*

```text
feat: agent-guided playbook replay with robust locator fallbacks
```

*Commit message example*

```text
docs: add v1.1.1 changelog entry
```

*Commit message example*

```text
fix: address P1+P2 reviewer comments from PR #6
```

*Commit message example*

```text
security: pre-publication audit fixes
```

*Commit message example*

```text
chore: mark all rebuild phases complete
```

*Commit message example*

```text
Merge pull request #6 from Nunezchef/claude/optimistic-mahavira
```

*Commit message example*

```text
fix: guard ObserverManager against double-start and verify task cleanup
```

*Commit message example*

```text
fix: self-correction-friendly error messages in bridge_record and bridge_replay
```

## Architecture

### Project Structure: Single Package

This project uses **hybrid** module organization.

### Guidelines

- This project uses a hybrid organization
- Follow existing patterns when adding new code

## Code Style

### Language: Python

### Naming Conventions

| Element | Convention |
|---------|------------|
| Files | snake_case |
| Functions | camelCase |
| Classes | PascalCase |
| Constants | SCREAMING_SNAKE_CASE |

### Import Style: Absolute Imports

### Export Style: Named Exports


*Preferred export style*

```typescript
// Use named exports
export function calculateTotal() { ... }
export const TAX_RATE = 0.1
export interface Order { ... }
```

## Testing

### Test Framework

No specific test framework detected — use the repository's existing test patterns.

### File Pattern: `*.test.ts`

### Test Types

- **Unit tests**: Test individual functions and components in isolation


## Error Handling

### Error Handling Style: Try-Catch Blocks


*Standard error handling pattern*

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('User-friendly message')
}
```

## Common Workflows

These workflows were detected from analyzing commit patterns.

### Feature Development

Standard feature implementation workflow

**Frequency**: ~14 times per month

**Steps**:
1. Add feature implementation
2. Add tests for feature
3. Update documentation

**Files typically involved**:
- `**/*.test.*`
- `**/api/**`

**Example commit sequence**:
```
chore: initialize rune project context
fix: keyboard forwarding, refresh/back buttons, captcha clicks
fix: back/refresh buttons use Runtime.evaluate, skip CDP events
```

### Feature Development With Tests And Docs

Implements a new feature or major compatibility layer, accompanied by targeted tests and sometimes documentation updates.

**Frequency**: ~3 times per month

**Steps**:
1. Implement feature logic (often in multiple core files).
2. Update or add related tests in tests/ directory.
3. Update documentation or prompts if relevant (README.md, CHANGELOG.md, or prompt files).

**Files typically involved**:
- `api/bridge.py`
- `bridge.py`
- `observer/manager.py`
- `observer/playbook_recorder.py`
- `observer/sitemap_learner.py`
- `tools/bridge_record.py`
- `tools/bridge_replay.py`
- `webui/phantom-bridge-store.js`
- `extensions/system_prompt/_45_browser_bridge.py`
- `tests/*.py`
- `CHANGELOG.md`
- `README.md`

**Example commit sequence**:
```
Implement feature logic (often in multiple core files).
Update or add related tests in tests/ directory.
Update documentation or prompts if relevant (README.md, CHANGELOG.md, or prompt files).
```

### Bugfix With Targeted Tests

Fixes a bug or regression and adds or updates tests to cover the fixed behavior.

**Frequency**: ~4 times per month

**Steps**:
1. Identify and fix the bug in the relevant source file(s).
2. Add or update a test in tests/ to cover the bug scenario.
3. Sometimes update documentation or comments to clarify the fix.

**Files typically involved**:
- `observer/manager.py`
- `observer/playbook_recorder.py`
- `observer/sitemap_learner.py`
- `tools/bridge_record.py`
- `tools/bridge_replay.py`
- `api/bridge.py`
- `webui/phantom-bridge-store.js`
- `tests/*.py`

**Example commit sequence**:
```
Identify and fix the bug in the relevant source file(s).
Add or update a test in tests/ to cover the bug scenario.
Sometimes update documentation or comments to clarify the fix.
```

### Ui Icon And Theme Refresh

Updates or replaces UI icons, SVGs, and related assets for branding or clarity across multiple UI locations.

**Frequency**: ~2 times per month

**Steps**:
1. Replace or update icon/image files (SVG, PNG) in webui/ and docs/.
2. Update HTML files to reference new icons.
3. Sometimes update README.md or other docs to reflect new branding.

**Files typically involved**:
- `webui/icon.png`
- `webui/thumbnail.png`
- `webui/main.html`
- `webui/bridge-modal.html`
- `webui/bridge.html`
- `extensions/webui/chat-input-bottom-actions-end/phantom-bridge-button.html`
- `docs/banner.png`
- `docs/ghost.png`
- `README.md`

**Example commit sequence**:
```
Replace or update icon/image files (SVG, PNG) in webui/ and docs/.
Update HTML files to reference new icons.
Sometimes update README.md or other docs to reflect new branding.
```

### System Prompt Or Agent Prompt Extension

Updates or adds to the system prompt extensions or agent tool prompts to improve model guidance or compatibility.

**Frequency**: ~2 times per month

**Steps**:
1. Edit or add files in extensions/system_prompt/ or extensions/prompts/.
2. Update or add related tests in tests/ if prompt logic is programmatic.
3. Sometimes update documentation to reflect new prompt behavior.

**Files typically involved**:
- `extensions/system_prompt/_45_browser_bridge.py`
- `extensions/prompts/agent.system.tool.bridge_replay.md`
- `extensions/prompts/agent.system.tool.browser_bridge.md`
- `tests/test_system_prompt.py`

**Example commit sequence**:
```
Edit or add files in extensions/system_prompt/ or extensions/prompts/.
Update or add related tests in tests/ if prompt logic is programmatic.
Sometimes update documentation to reflect new prompt behavior.
```

### Documentation And Changelog Update

Updates documentation and/or changelog files to reflect recent changes, new features, or releases.

**Frequency**: ~2 times per month

**Steps**:
1. Edit README.md, CHANGELOG.md, or add new docs/ assets.
2. Sometimes update .gitignore or index.yaml for packaging/submission.
3. May include banner or icon updates for branding.

**Files typically involved**:
- `README.md`
- `CHANGELOG.md`
- `docs/banner.png`
- `docs/index.yaml`
- `docs/thumbnail.png`
- `.gitignore`

**Example commit sequence**:
```
Edit README.md, CHANGELOG.md, or add new docs/ assets.
Sometimes update .gitignore or index.yaml for packaging/submission.
May include banner or icon updates for branding.
```

### Import Path Correction For Plugin Context

Fixes import paths in Python modules to ensure compatibility with different plugin or execution contexts.

**Frequency**: ~2 times per month

**Steps**:
1. Identify modules with incorrect or brittle import paths.
2. Change to relative or context-agnostic imports.
3. Test in both standalone and plugin-invoked contexts.

**Files typically involved**:
- `observer/playbook_recorder.py`
- `observer/sitemap_learner.py`
- `extensions/python/message_loop_start/_30_browser_bridge_profile.py`
- `bridge.py`

**Example commit sequence**:
```
Identify modules with incorrect or brittle import paths.
Change to relative or context-agnostic imports.
Test in both standalone and plugin-invoked contexts.
```


## Best Practices

Based on analysis of the codebase, follow these practices:

### Do

- Use conventional commit format (feat:, fix:, etc.)
- Follow *.test.ts naming pattern
- Use snake_case for file names
- Prefer named exports

### Don't

- Don't write vague commit messages
- Don't skip tests for new features
- Don't deviate from established patterns without discussion

---

*This skill was auto-generated by [ECC Tools](https://ecc.tools). Review and customize as needed for your team.*
