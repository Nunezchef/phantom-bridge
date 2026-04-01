```markdown
# phantom-bridge Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you how to contribute to the `phantom-bridge` project, a Python-based plugin that bridges backend logic with a web-based UI. You'll learn the coding conventions, commit patterns, and step-by-step workflows for adding features, fixing bugs, updating UI assets, maintaining documentation, improving system prompts, and applying security hardening. Whether you're working on backend Python, frontend JS/HTML, or configuration files, this guide will help you follow the project's standards and processes.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for Python files and directories.  
  Example:  
  ```
  observer/playbook_recorder.py
  tools/bridge_record.py
  ```

- **Import Style:**  
  Use absolute imports in Python.  
  Example:  
  ```python
  from observer.manager import Manager
  from tools.bridge_record import record_bridge
  ```

- **Export Style:**  
  Use named exports in JS modules.  
  Example:  
  ```js
  export function subscribeToBridgeEvents() { ... }
  ```

- **Commit Messages:**  
  Use [Conventional Commits](https://www.conventionalcommits.org/):  
  - Prefixes: `fix`, `feat`, `docs`, `chore`
  - Example:  
    ```
    feat: add replay support for bridge events in observer
    fix: handle unicode sanitization in bridge replay
    ```

- **Frontend Assets:**  
  - HTML, JS, and image assets for the web UI are in `webui/`.
  - Use descriptive, lower-case file names.

## Workflows

### Feature Development with Backend, Frontend, and Config
**Trigger:** When adding a new user-facing capability or workflow  
**Command:** `/new-feature`

1. Implement backend logic in Python (`api/bridge.py`, `observer/*.py`, `tools/*.py`).
2. Update or add API endpoints as needed.
3. Modify or extend configuration in `plugin.yaml`.
4. Update or create frontend UI components (`webui/*.html`, `webui/*.js`).
5. Update the store logic to subscribe to new events or state (`webui/phantom-bridge-store.js`).

**Example:**
```python
# api/bridge.py
def new_feature_endpoint():
    # Backend logic here
    pass
```
```js
// webui/phantom-bridge-store.js
export function subscribeToNewFeature() {
    // Store logic for new feature
}
```

---

### Bugfix with Associated Test or Integration Update
**Trigger:** When resolving a defect and ensuring it's covered by tests  
**Command:** `/bugfix`

1. Identify and fix the bug in the relevant Python or JS file.
2. Update or add a test in `tests/` to cover the fixed behavior.
3. Update related logic in `webui/` or `tools/` if needed.
4. Commit both the fix and the test together.

**Example:**
```python
# observer/manager.py
def sanitize_unicode(input_str):
    return input_str.encode("utf-8", errors="replace").decode("utf-8")
```
```python
# tests/test_unicode_sanitization.py
def test_sanitize_unicode():
    assert sanitize_unicode("café") == "café"
```

---

### UI Icon or Theme Update
**Trigger:** When refreshing the look and feel or fixing icon-related issues in the UI  
**Command:** `/update-ui-icon`

1. Update or replace icon files (PNG, SVG) in `webui/` or `docs/`.
2. Modify HTML files to reference new icons or SVGs.
3. Update JS or CSS to ensure correct rendering if needed.
4. Commit all related assets and markup changes together.

**Example:**
```html
<!-- webui/main.html -->
<img src="icon.png" alt="Bridge Icon" />
```

---

### Documentation and README Update
**Trigger:** When documenting a release, summarizing changes, or improving onboarding  
**Command:** `/update-docs`

1. Edit `README.md` to add highlights, banners, or usage instructions.
2. Update `CHANGELOG.md` with new entries for releases.
3. Add or update documentation assets (`docs/*.png`, `docs/index.yaml`).

**Example:**
```markdown
## New in v1.2.0
- Added bridge replay feature
- Improved Unicode handling
```

---

### System Prompt or Agent Extension Update
**Trigger:** When improving agent guidance, compatibility, or prompt logic  
**Command:** `/update-system-prompt`

1. Edit or extend `extensions/system_prompt/_45_browser_bridge.py`.
2. Update or add prompt markdown files in `extensions/prompts/`.
3. Add or update tests in `tests/test_system_prompt.py` if needed.

**Example:**
```python
# extensions/system_prompt/_45_browser_bridge.py
SYSTEM_PROMPT = "You are now connected to the Phantom Bridge."
```

---

### Security or Audit Hardening
**Trigger:** When addressing audit findings or hardening the plugin before release  
**Command:** `/security-audit`

1. Update config files (`default_config.yaml`, `requirements.txt`, `plugin.yaml`).
2. Change sensitive defaults (e.g., `bind_address`, CSRF settings).
3. Remove development artifacts or sensitive files from git.
4. Update `.gitignore` as needed.

**Example:**
```yaml
# .gitignore
*.pyc
__pycache__/
.env
```

## Testing Patterns

- **Framework:** Unknown (no explicit framework detected)
- **File Pattern:** Test files are named as `test_*.py` in the `tests/` directory.
- **Test Example:**
  ```python
  # tests/test_cache_control.py
  def test_cache_control_headers():
      response = client.get("/api/bridge")
      assert "Cache-Control" in response.headers
  ```
- **Integration:** When fixing bugs, always add or update a corresponding test.

## Commands

| Command              | Purpose                                                        |
|----------------------|----------------------------------------------------------------|
| /new-feature         | Start a feature spanning backend, API, config, and frontend    |
| /bugfix              | Fix a bug and add/update a test                                |
| /update-ui-icon      | Update UI icons, SVGs, or theme assets                         |
| /update-docs         | Update documentation, README, or changelog                     |
| /update-system-prompt| Update system prompt logic or agent extension files            |
| /security-audit      | Apply security fixes or audit recommendations                  |
```
