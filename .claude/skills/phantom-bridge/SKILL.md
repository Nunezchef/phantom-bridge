```markdown
# phantom-bridge Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development practices, coding conventions, and collaborative workflows used in the `phantom-bridge` Python project. The repository is designed for backend and frontend integration, with a focus on modularity, maintainability, and clear documentation. You will learn how to contribute features, fix bugs, update UI elements, polish documentation, harden security, and ensure compatibility with evolving backend protocols.

---

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.  
  *Example:*  
  ```
  bridge.py
  observer/event_handler.py
  api/request_parser.py
  ```

- **Import Style:**  
  Use absolute imports for all modules.  
  *Example:*  
  ```python
  # Correct
  from api.request_parser import parse_request

  # Avoid
  from .request_parser import parse_request
  ```

- **Export Style:**  
  Use named exports (explicitly define what is exported from a module).  
  *Example:*  
  ```python
  # In observer/event_handler.py
  __all__ = ['EventHandler']

  class EventHandler:
      ...
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes: `feat`, `fix`, `docs`, `chore`.  
  *Example:*  
  ```
  feat: add websocket support to bridge.py
  fix: correct observer event parsing for edge cases
  docs: update README with API usage examples
  chore: update dependencies in requirements.txt
  ```

---

## Workflows

### Feature Development with Tests and Docs
**Trigger:** When adding a new capability or major improvement  
**Command:** `/feature`

1. Implement feature logic in core modules (`bridge.py`, `observer/*.py`, `api/*.py`, etc.)
2. Update or add frontend/UI components if needed (`webui/*.js`, `webui/*.html`)
3. Add or update automated tests covering the new feature (`tests/test_*.py`)
4. Update documentation or changelog to reflect the new feature (`README.md`, `CHANGELOG.md`)

*Example:*
```python
# bridge.py
class NewBridgeFeature:
    def run(self):
        pass  # feature logic here

# tests/test_new_feature.py
def test_new_bridge_feature():
    feature = NewBridgeFeature()
    assert feature.run() is None
```

---

### Bugfix with Targeted Tests
**Trigger:** When resolving a reported bug or regression  
**Command:** `/bugfix`

1. Identify and fix the bug in the relevant source file(s)
2. Add or update a targeted test in `tests/test_*.py` to reproduce and verify the fix
3. Optionally update documentation or changelog if the fix is user-facing

*Example:*
```python
# observer/event_handler.py
def handle_event(event):
    if event is None:
        return False  # bugfix: handle None event
    # existing logic

# tests/test_event_handler.py
def test_handle_event_none():
    assert handle_event(None) is False
```

---

### Frontend UI Icon or Style Update
**Trigger:** When improving or changing the look and feel of the UI, especially icons  
**Command:** `/ui-icon-update`

1. Replace or update icon/image files (`webui/icon.png`, `webui/thumbnail.png`, etc.)
2. Update references to icons in HTML/JS files
3. Test UI to ensure new icons/styles render correctly

*Example:*
```html
<!-- webui/index.html -->
<img src="icon.png" alt="App Icon">
```

---

### Documentation and README Polish
**Trigger:** When clarifying, polishing, or updating project documentation  
**Command:** `/docs-update`

1. Edit `README.md` for clarity, new sections, or updated instructions
2. Add or update images/banners in `docs/`
3. Update `CHANGELOG.md` with new entries
4. Optionally update `.gitignore` for documentation-related artifacts

*Example:*
```markdown
# README.md
## New Feature
Description of the new feature...

# CHANGELOG.md
## [1.2.0] - 2024-06-10
### Added
- New bridge feature
```

---

### Security or Audit Hardening
**Trigger:** When addressing audit findings or hardening the codebase  
**Command:** `/security-audit`

1. Update configuration files for security (`requirements.txt`, `default_config.yaml`)
2. Remove sensitive or development-only files from the repo
3. Update `.gitignore` to exclude new sensitive/artifact paths
4. Apply code changes to restrict access or enable protections (e.g., CSRF, bind_address)

*Example:*
```yaml
# default_config.yaml
bind_address: "127.0.0.1"
enable_csrf: true
```
```gitignore
# .gitignore
.rune/
*.env
```

---

### Backend Integration or Compatibility Update
**Trigger:** When adapting the backend for a new platform version or protocol  
**Command:** `/compat-update`

1. Update backend source files for compatibility (`bridge.py`, `observer/*.py`, `api/*.py`, `extensions/system_prompt/*.py`)
2. Update or add tests to cover new integration points
3. Update frontend or UI logic if new events/data are exposed
4. Document changes in `CHANGELOG.md`

*Example:*
```python
# api/new_protocol.py
def handle_new_protocol(data):
    # compatibility logic
    pass
```

---

## Testing Patterns

- **Test Framework:** Not explicitly detected, but Python tests are named as `tests/test_*.py`.
- **Test File Naming:**  
  All test files use `snake_case` and start with `test_`.  
  *Example:*  
  ```
  tests/test_bridge.py
  tests/test_event_handler.py
  ```

- **Test Example:**
  ```python
  # tests/test_bridge.py
  def test_bridge_initialization():
      bridge = Bridge()
      assert bridge.is_ready()
  ```

---

## Commands

| Command          | Purpose                                                        |
|------------------|----------------------------------------------------------------|
| /feature         | Start a new feature with tests and documentation               |
| /bugfix          | Fix a bug and add/update a targeted test                       |
| /ui-icon-update  | Update UI icons or visual styles                               |
| /docs-update     | Polish or update documentation and changelogs                  |
| /security-audit  | Apply security fixes or audit recommendations                  |
| /compat-update   | Update backend for new API/protocol/platform compatibility     |
```
