# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-31
**Plugin:** phantom_bridge v1.1.1
**Framework:** Agent Zero (A0)

## OVERVIEW
A0 plugin: remote browser viewer (noVNC) for auth → A0 inherits sessions, learns patterns, replays workflows. Display layer = noVNC (Xvfb + x11vnc + websockify). Observation layer = CDP (Chrome DevTools Protocol).

## STRUCTURE
```
phantom_bridge/
├── bridge.py              # BrowserBridge singleton — Chromium + noVNC lifecycle
├── cookie_crypt.py        # Fernet encrypt/decrypt for cookie values at rest
├── screencast.py          # CDP screencast manager (fallback when noVNC port unavailable)
├── ws_broadcast.py        # WebSocket broadcast for real-time UI events
├── execute.py             # Dependency installer (apt: x11vnc, novnc, xvfb, xdotool, chromium)
├── hooks.py               # A0 framework lifecycle hooks (install)
├── default_config.yaml    # Plugin defaults (port, profile, headless, viewport)
├── plugin.yaml            # A0 plugin manifest (name, version, settings sections)
├── requirements.txt       # websockets + cryptography
├── observer/              # Three-tier CDP observation system
├── tools/                 # A0 tool implementations (extends helpers.tool.Tool)
├── api/                   # HTTP API handlers (extends helpers.api.ApiHandler)
├── extensions/            # A0 extension hooks (numeric prefix = load order)
├── webui/                 # Alpine.js sidebar panel + noVNC iframe
├── docs/                  # Documentation + assets
└── tests/                 # pytest-style tests
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Start/stop bridge | `bridge.py` | Singleton — `_bridge` module var |
| Cookie encryption | `cookie_crypt.py` | Fernet, key at `data/.cookie_key` |
| Auth detection | `observer/auth_registry.py` | Cookie diffing + auth URL patterns |
| Sitemap learning | `observer/sitemap_learner.py` | URL pattern mapping per domain |
| Playbook recording | `observer/playbook_recorder.py` | Replayable navigation sequences |
| Observer orchestration | `observer/manager.py` | Shares single CDP connection |
| A0 tools | `tools/` | One tool per file, extends `Tool` |
| HTTP API | `api/bridge.py` | Start/stop/status/auth/sitemaps/playbooks |
| Profile sharing | `extensions/python/message_loop_start/_30_browser_bridge_profile.py` | Monkeypatches `browser_agent.State.get_user_data_dir()` |
| System prompt injection | `extensions/system_prompt/_45_browser_bridge.py` | Adds bridge awareness to A0 |
| WebUI store | `webui/phantom-bridge-store.js` | Alpine store, polls API every 5s |
| noVNC viewer | `webui/bridge.html` | Remote browser iframe |
| Tool docs for A0 | `extensions/prompts/` | `agent.system.tool.*.md` files |
| Real-time events | `ws_broadcast.py` | WebSocket push to UI |

## CONVENTIONS
- **Naming:** snake_case files/functions, PascalCase classes
- **Imports:** `from __future__ import annotations` at top of every module
- **Deferred imports:** A0 framework imports inside method bodies (avoid circular imports, allow standalone execution)
- **A0 imports:** `from usr.plugins.phantom_bridge.module import X` — no sys.path hacks
- **Config loading:** `_load_config()` tries `helpers.plugins.get_plugin_config()` first, falls back to `default_config.yaml`
- **Error handling:** `try/except` with `logging.warning` for non-critical; `RuntimeError` for critical
- **Extension load order:** `_30_` and `_45_` numeric prefixes control A0's execution order
- **Observer pattern:** CDP events via `CDPClient.subscribe()` callbacks (sync or async)
- **Tool pattern:** extends `helpers.tool.Tool`, implements `async execute(**kwargs) -> Response`
- **API pattern:** extends `helpers.api.ApiHandler`, implements `async process(input, request) -> dict`

## ANTI-PATTERNS
- **NEVER** commit `data/` directory — gitignored, contains sessions/cookies/profiles
- **NEVER** use `sys.path` hacks — use `from usr.plugins.phantom_bridge.*` imports
- **NEVER** suppress type errors with `as any` or `# type: ignore`
- **DO NOT** refactor while fixing bugs — fix minimally, then refactor separately
- **DO NOT** hard-code credentials or API keys

## UNIQUE STYLES
- **Singleton bridge:** `_bridge` module-level variable in `bridge.py`; one Chromium per container
- **Profile sharing:** Extension monkeypatches A0's `browser_agent.State` to return bridge's profile dir
- **Cookie encryption:** Values encrypted at rest (Fernet); names/metadata in plaintext for structure inspection
- **CDP reconnect:** Exponential backoff (0.5s initial, 5s max, 10 attempts)
- **API cache opt-out:** `Cache-Control: no-store` on all bridge API responses (A0 v1.5 caching)
- **Unicode sanitization:** Page titles/DOM events sanitized before storage (lone surrogate protection)
- **Screencast fallback:** When noVNC port 6080 unavailable, streams through A0's port 5050

## COMMANDS
```bash
# Install Python deps
pip install -r requirements.txt

# Install system deps (inside container)
python execute.py

# Dev: copy plugin to A0 and restart
cp -r phantom_bridge /path/to/a0/usr/plugins/

# Run tests
pytest tests/
```

## NOTES
- `data/` created at runtime — `.cookie_key`, `cookies/`, `profile/`, `auth_registry.json`, `sitemaps/`, `playbooks/`
- noVNC serves on port 6080 (configurable via `novnc_port` in `default_config.yaml`)
- CDP port 9222 (configurable via `remote_debug_port`)
- `headless: false` = noVNC mode; `headless: true` = CDP-only (no display rendering)
- Alpine store polls `/plugins/phantom_bridge/bridge` every 10s for live state
- `ObserverManager.start()` is idempotent; `stop()` cancels and awaits all background tasks
- Version: 1.1.1 (WebSocket push, self-correction errors, small-model prompt, Unicode sanitization)
