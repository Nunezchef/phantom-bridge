```markdown
# phantom-bridge Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and collaboration workflows used in the `phantom-bridge` Python codebase. The repository centers on a backend bridge system with observer modules, CLI tools, and a WebUI, but does not use a formal web framework. Development follows clear commit conventions, modular Python design, and a set of well-defined workflows for features, bugfixes, API changes, documentation, UI work, and refactoring.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for Python files and directories.  
  _Example:_  
  ```
  observer/metrics.py
  tools/bridge_record.py
  ```

- **Import Style:**  
  Use absolute imports for all modules.  
  _Example:_  
  ```python
  import observer.metrics
  from tools.bridge_record import BridgeRecorder
  ```

- **Export Style:**  
  Use named exports (explicit functions/classes).  
  _Example:_  
  ```python
  def start_bridge():
      ...
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/), using prefixes like `feat`, `fix`, `docs`, `chore`.  
  _Example:_  
  ```
  feat(observer): add session health monitoring to manager
  fix(tools): handle missing replay file edge case
  ```

- **Directory Structure:**  
  - `api/` — API endpoint handlers
  - `observer/` — Observer modules and managers
  - `tools/` — CLI and utility scripts
  - `webui/` — JS and HTML for the WebUI
  - `tests/` — Python test files (`test_*.py`)
  - `extensions/` — Prompts and extension modules
  - `docs/` — Documentation

## Workflows

### Feature Development with API, Tool, and UI
**Trigger:** When adding a significant new capability that spans backend API, core logic, tools/CLIs, and WebUI.  
**Command:** `/feature`

1. Edit or add backend logic in `api/bridge.py` and/or `bridge.py`.
2. Update or add observer modules, e.g., `observer/manager.py`, `observer/auth_registry.py`, `observer/metrics.py`.
3. Add or update tool scripts, e.g., `tools/bridge_record.py`, `tools/bridge_replay.py`.
4. Update or add WebUI files:  
   - JS: `webui/phantom-bridge-store.js`  
   - HTML: `webui/main.html`, `webui/bridge-modal.html`
5. Update `plugin.yaml` if new settings or endpoints are introduced.
6. Optionally, add or update prompts/extensions in `extensions/prompts/*.md` if agent instructions change.

_Example:_  
```python
# api/bridge.py
def add_health_endpoint():
    # New API endpoint logic
    ...
```
```js
// webui/phantom-bridge-store.js
export function showHealthStatus(status) {
    ...
}
```

---

### Bugfix or Hardening with Targeted Tests
**Trigger:** When fixing a specific bug, regression, or reviewer comment, especially in observer or tools modules.  
**Command:** `/bugfix`

1. Edit the affected backend, observer, or tool file(s) to fix the bug or add a guard.
2. Add or update a test file (`tests/test_*.py`) to cover the fixed behavior.
3. Commit both code and test changes together.

_Example:_  
```python
# observer/metrics.py
def get_metric(name):
    if name not in metrics:
        return None  # Guard added
    return metrics[name]
```
```python
# tests/test_metrics.py
def test_get_metric_missing():
    assert get_metric('nonexistent') is None
```

---

### API Endpoint Addition or Modification
**Trigger:** When exposing new backend functionality via an API endpoint.  
**Command:** `/api-endpoint`

1. Edit or add endpoint handler in `api/bridge.py`.
2. Update `plugin.yaml` to document/register the endpoint.
3. Optionally, update/add a tool script or WebUI integration.
4. Optionally, add or update tests for the endpoint.

_Example:_  
```python
# api/bridge.py
def new_endpoint():
    ...
```
```yaml
# plugin.yaml
endpoints:
  - name: new_endpoint
    path: /api/new
    method: POST
```

---

### Documentation and Changelog Update
**Trigger:** When documenting new features, fixes, or preparing for a release.  
**Command:** `/docs`

1. Edit `README.md` to reflect new features or changes.
2. Add or update `CHANGELOG.md` with version entries.
3. Optionally, add or update other docs (`docs/*.md`, `docs/*.yaml`, `docker-compose.yml`).

_Example:_  
```markdown
## [1.2.0] - 2024-06-01
### Added
- Health monitoring endpoint
```

---

### WebUI Feature or Bugfix
**Trigger:** When adding, improving, or fixing a UI element or behavior.  
**Command:** `/webui`

1. Edit or add JS logic in `webui/phantom-bridge-store.js`.
2. Edit or add HTML component files (`webui/bridge-modal.html`, `webui/main.html`, etc.).
3. Optionally, coordinate with backend or API changes.

_Example:_  
```js
// webui/phantom-bridge-store.js
export function updateSessionList(sessions) {
    ...
}
```
```html
<!-- webui/bridge-modal.html -->
<div id="session-list"></div>
```

---

### Refactor or Centralize Shared Logic
**Trigger:** When DRYing up code, centralizing configuration, or fixing import/path issues across modules.  
**Command:** `/refactor`

1. Create or update a shared module (e.g., `data_paths.py`).
2. Update all modules to use the new shared logic.
3. Update or fix tests to use the new logic.

_Example:_  
```python
# data_paths.py
def get_data_dir():
    ...
```
```python
# observer/manager.py
from data_paths import get_data_dir
```

---

## Testing Patterns

- **Test File Naming:**  
  All tests are Python files named `test_*.py` in the `tests/` directory.

- **Test Framework:**  
  Not explicitly specified; likely uses `pytest` or standard `unittest`.

- **Test Example:**  
  ```python
  # tests/test_bridge.py
  def test_bridge_startup():
      bridge = Bridge()
      assert bridge.is_running()
  ```

- **Other Patterns:**  
  - Tests are updated or added alongside bugfixes and new features.
  - Each test targets a specific function or module.

## Commands

| Command      | Purpose                                                      |
|--------------|--------------------------------------------------------------|
| /feature     | Start a new feature spanning backend, tools, and WebUI       |
| /bugfix      | Fix a bug and add/update targeted tests                      |
| /api-endpoint| Add or modify an API endpoint and update plugin.yaml         |
| /docs        | Update documentation and changelogs                          |
| /webui       | Implement or fix a WebUI feature                             |
| /refactor    | Centralize or refactor shared logic across modules           |
```
