# TOOLS MODULE

## OVERVIEW
A0 tool implementations — one tool per file. Each extends `helpers.tool.Tool` and implements `async execute(**kwargs) -> Response`.

## STRUCTURE
```
tools/
├── bridge_open.py           # browser_bridge_open — start bridge + noVNC viewer
├── bridge_close.py          # browser_bridge_close — stop bridge (sessions persist)
├── bridge_status.py         # browser_bridge_status — status, pages, authenticated domains
├── bridge_auth.py           # bridge_auth — query auth registry
├── bridge_sitemap.py        # bridge_sitemap — query learned sitemaps per domain
├── bridge_record.py         # bridge_record — start/stop playbook recording
├── bridge_replay.py         # bridge_replay — replay saved playbooks
├── bridge_health.py         # bridge_health — check session health
└── bridge_decrypt_cookies.py # bridge_decrypt_cookies — decrypt cookies for HTTP requests
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Start bridge | `bridge_open.py` | Creates bridge from config, calls `bridge.start()` |
| Stop bridge | `bridge_close.py` | Calls `bridge.stop()`, observer cleanup |
| Query status | `bridge_status.py` | Returns bridge status + observer data |
| Auth queries | `bridge_auth.py` | Reads `data/auth_registry.json` |
| Cookie decryption | `bridge_decrypt_cookies.py` | Uses `cookie_crypt.decrypt_for_domain()` |
| Recording | `bridge_record.py` | Delegates to `playbook_recorder` |
| Replay | `bridge_replay.py` | Loads + executes saved playbooks |

## CONVENTIONS
- **Deferred imports:** All imports from `bridge.py` and `observer/` inside `execute()` body
- **Config loading:** `config = self._load_config()` at start of every tool
- **Error format:** Return `Response(message=..., break_loop=False)` with self-correction hints
- **Bridge access:** `from usr.plugins.phantom_bridge.bridge import get_bridge, create_bridge_from_config`
- **Tool naming:** Class name = PascalCase of tool name (e.g., `BrowserBridgeOpen`)

## ANTI-PATTERNS
- **DO NOT** import `bridge` at module level — causes import errors when running outside A0
- **DO NOT** suppress errors silently — return structured error messages with JSON call examples
- **DO NOT** create new bridge instances — always use `get_bridge()` first, then `create_bridge_from_config()`

## NOTES
- Tool names registered with A0: `browser_bridge_open`, `browser_bridge_close`, etc. (snake_case)
- Error messages include canonical JSON examples for A0 v1.5 self-correction
- All tools are idempotent where possible (e.g., `bridge_open` returns status if already running)
