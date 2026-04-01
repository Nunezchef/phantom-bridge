```markdown
# phantom-bridge Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `phantom-bridge` Python codebase. The project is a backend-focused bridge system with a modular architecture, supporting API endpoints, frontend UI, plugin configuration, and agent prompt integration. You'll learn how to implement features, fix bugs, update the UI, manage documentation, and apply security practices in a consistent, maintainable way.

---

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for Python files and directories.  
  *Example:*  
  ```
  api/bridge.py
  observer/event_handler.py
  tools/utilities.py
  ```

- **Import Style:**  
  Use absolute imports within Python modules.  
  *Example:*  
  ```python
  # Correct
  from api.bridge import BridgeAPI

  # Avoid
  from .bridge import BridgeAPI
  ```

- **Export Style:**  
  Use named exports (explicit function/class definitions).  
  *Example:*  
  ```python
  # api/bridge.py
  class BridgeAPI:
      pass

  def get_status():
      pass
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes:  
  - `fix:` for bug fixes  
  - `feat:` for new features  
  - `docs:` for documentation  
  - `chore:` for maintenance  
  *Example:*  
  ```
  feat: add batch processing to observer module
  fix: handle null payloads in bridge API
  ```

---

## Workflows

### Feature Development, Implementation, Tests & Docs
**Trigger:** When adding a new capability or major feature  
**Command:** `/feature`

1. Implement feature logic in backend Python modules (`api/`, `observer/`, `tools/`)
2. Update or add supporting frontend files (`webui/`, `extensions/webui/`) if needed
3. Update or add API endpoints (e.g., `api/bridge.py`)
4. Update `plugin.yaml` or config if new settings are introduced
5. Write or update tests in `tests/` for the new feature
6. Update documentation (`README.md`, `CHANGELOG.md`) if user-facing

*Example:*
```python
# api/bridge.py
def new_feature():
    """Implements the new capability."""
    pass
```
```yaml
# plugin.yaml
settings:
  enable_new_feature: true
```

---

### API Endpoint Addition or Modification
**Trigger:** When exposing new backend functionality to frontend or clients  
**Command:** `/add-endpoint`

1. Implement or update endpoint in `api/bridge.py` (or related `api/*.py`)
2. Update `plugin.yaml` if endpoint or settings change
3. Update frontend store/UI to consume the new endpoint (`webui/phantom-bridge-store.js`, `webui/*.html`)
4. Write or update tests in `tests/` for endpoint behavior

*Example:*
```python
# api/bridge.py
def get_bridge_status():
    return {"status": "ok"}
```
```js
// webui/phantom-bridge-store.js
fetch('/api/bridge/status').then(...)
```

---

### Frontend UI Component Update
**Trigger:** When improving or adding to the user interface  
**Command:** `/ui-update`

1. Edit or add HTML component in `webui/` or `extensions/webui/`
2. Update supporting JS store logic if needed (`webui/phantom-bridge-store.js`)
3. Update icons or images (`webui/icon.png`, `webui/thumbnail.png`, etc.)
4. Update `README.md` or docs if user-facing changes

*Example:*
```html
<!-- webui/new_modal.html -->
<div class="modal">New Feature Modal</div>
```
```js
// webui/phantom-bridge-store.js
export function openNewModal() { /* ... */ }
```

---

### Bugfix with Targeted Tests
**Trigger:** When resolving a defect and preventing recurrence  
**Command:** `/bugfix`

1. Identify and fix bug in backend or frontend source (`api/`, `observer/`, `tools/`, `webui/`)
2. Add or update test(s) in `tests/` to cover the fixed scenario
3. Optionally update documentation if user-facing

*Example:*
```python
# tools/utilities.py
def safe_parse(data):
    if data is None:
        return {}
    # ...rest of logic
```
```python
# tests/test_utilities.py
def test_safe_parse_handles_none():
    assert safe_parse(None) == {}
```

---

### System Prompt or Agent Integration Update
**Trigger:** When changing agent interaction or prompt logic  
**Command:** `/prompt-update`

1. Edit system prompt or agent prompt files (`extensions/system_prompt/_45_browser_bridge.py`, `extensions/prompts/agent.system.tool.*.md`)
2. Update backend logic if prompt structure or tool interface changes
3. Add or update tests in `tests/test_system_prompt.py` or related
4. Update documentation if user-facing

*Example:*
```python
# extensions/system_prompt/_45_browser_bridge.py
SYSTEM_PROMPT = "You are now connected to the Phantom Bridge."
```

---

### Security or Audit Hardening
**Trigger:** When addressing security audit findings or hardening the system  
**Command:** `/security-fix`

1. Update API/config to restrict access or fix vulnerabilities (`api/*.py`, `default_config.yaml`, `requirements.txt`)
2. Update `.gitignore` to exclude sensitive or dev artifacts
3. Remove or clean up development artifacts from repo
4. Document changes in `README.md` or `CHANGELOG.md`

*Example:*
```python
# api/bridge.py
def secure_endpoint(user):
    if not user.is_admin:
        raise PermissionError("Admin only")
```
```gitignore
# .gitignore
*.env
*.pyc
```

---

### Documentation Release Update
**Trigger:** When preparing for a release or improving documentation  
**Command:** `/docs-update`

1. Update `README.md` with new features, instructions, or highlights
2. Add or update `CHANGELOG.md` with recent changes
3. Add or update `docs/` assets (banner, index.yaml, thumbnails, etc.)
4. Update `plugin.yaml` version or description if needed

*Example:*
```markdown
# CHANGELOG.md
## [1.2.0] - 2024-06-01
### Added
- Batch processing in observer module
```

---

## Testing Patterns

- **Framework:** Unknown (custom or standard Python testing)
- **File Pattern:** Python tests are in `tests/*.py`
- **Test Naming:** Use descriptive function names for test cases
- **Example:**
  ```python
  # tests/test_bridge.py
  def test_bridge_returns_status_ok():
      result = get_bridge_status()
      assert result["status"] == "ok"
  ```
- **Note:** There are also references to `*.test.ts` (TypeScript), but Python tests are primary.

---

## Commands

| Command         | Purpose                                                 |
|-----------------|---------------------------------------------------------|
| /feature        | Start a new feature with implementation and docs         |
| /add-endpoint   | Add or modify an API endpoint                           |
| /ui-update      | Update or add a frontend UI component                   |
| /bugfix         | Fix a bug and add/update regression tests               |
| /prompt-update  | Update system prompt or agent integration logic         |
| /security-fix   | Apply security fixes or audit recommendations           |
| /docs-update    | Update documentation and changelogs for a release       |
```
