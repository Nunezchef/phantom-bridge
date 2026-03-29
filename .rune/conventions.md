# Conventions

## Naming
- Files: snake_case (`bridge_open.py`, `cdp_client.py`, `auth_registry.py`)
- Classes: PascalCase (`BrowserBridge`, `CDPClient`, `AuthRegistry`, `ObserverManager`)
- Functions/methods: snake_case (`create_bridge_from_config`, `_on_page_loaded`)
- Private methods: leading underscore (`_resolve_chromium`, `_wait_for_devtools`)
- Constants: UPPER_SNAKE_CASE (`_AUTH_URL_PATTERNS`, `_MAX_CONNECT_ATTEMPTS`)
- Module-level singletons: leading underscore (`_bridge`, `_patched`)

## Import Style
- `from __future__ import annotations` at top of every Python module
- Standard library first, then third-party (`websockets`), then A0 framework (`helpers.*`), then local (`observer.*`, `bridge`)
- A0 framework imports deferred inside method bodies (not at module level) to avoid circular import issues when plugin loads outside A0 context
- Tools import from `plugins.browser_bridge.bridge` (full plugin path) inside execute()

## Error Handling
- Non-critical: try/except with `logger.warning()` — observers failing shouldn't crash the bridge
- Critical: raise `RuntimeError` with actionable message (e.g., "No Chromium binary found. Install via: playwright install chromium")
- Observer layers use optional imports with try/except ImportError for graceful degradation (L2 and L3 are optional)

## Architecture Patterns
- One tool per file in `tools/` extending `helpers.tool.Tool`
- One API handler per file in `api/` extending `helpers.api.ApiHandler`
- One extension per file in `extensions/` extending `helpers.extension.Extension`
- Observer layers share a single `CDPClient` WebSocket connection
- `ObserverManager` owns the CDPClient and distributes it to all observers
- CDP event dispatch: subscribe callbacks can be sync or async (auto-detected)

## Config Pattern
- Every tool and extension has a `_load_config()` method
- Priority: A0's `get_plugin_config()` → fallback to `default_config.yaml` → empty dict
- Config keys match YAML keys exactly (snake_case)

## Data Persistence
- JSON files in `data/` directory (relative to plugin root)
- Auth registry: single file `data/auth_registry.json`
- Sitemaps: per-domain files in `data/sitemaps/`
- Playbooks: per-recording files in `data/playbooks/`
- Browser profile: `data/profile/` (Chromium user data directory)

## Frontend (WebUI)
- Alpine.js stores via A0's `createStore()` from `/js/AlpineStore.js`
- API calls via A0's `callJsonApi()` from `/js/api.js`
- CSS uses `color-mix(in srgb, currentColor %, transparent)` for theme adaptation
- 10-second polling interval for status updates
