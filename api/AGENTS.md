# API MODULE

## OVERVIEW
HTTP API handlers for WebUI communication. Extends `helpers.api.ApiHandler`. All responses opt out of A0 v1.5 caching via `Cache-Control: no-store`.

## STRUCTURE
```
api/
├── bridge.py            # BridgeHandler — start/stop/status/auth/sitemaps/playbooks/cookies
├── proxy.py             # CDP page list proxy — forwards Chrome DevTools page listing
├── screencast.py        # Screencast API — CDP frame streaming endpoint
└── vnc_proxy.py         # VNC proxy — WebSocket proxy for noVNC viewer
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Bridge status/start/stop | `bridge.py` → `BridgeHandler` | Main API — handles all bridge actions |
| Cookie management | `bridge.py` → `_export_cookies()`, `_delete_cookies()` | Encrypted cookie operations |
| CDP page listing | `proxy.py` | Proxies `http://127.0.0.1:9222/json/list` |
| Screencast frames | `screencast.py` | CDP screencast streaming |
| VNC WebSocket | `vnc_proxy.py` | Bridges noVNC WebSocket to x11vnc |

## CONVENTIONS
- **Base class:** `BridgeHandler` extends `ApiHandler`, overrides `handle_request()` to add `Cache-Control: no-store`
- **Action routing:** Single endpoint with `action` param — `status`, `start`, `stop`, `auth_registry`, `sitemaps`, `playbooks`, `cookies`, `export_cookies`, `delete_cookies`
- **Deferred imports:** All `bridge.py` and `observer/` imports inside method bodies
- **Response format:** Returns `dict` with `ok: bool`, data fields, or `error: str` on failure
- **Plugin root:** `_plugin_root = Path(__file__).resolve().parent.parent` — used for data file paths

## ANTI-PATTERNS
- **DO NOT** cache bridge API responses — status/cookie/auth data must always be live
- **DO NOT** import bridge at module level — causes errors when running outside A0
- **DO NOT** return plaintext cookie values — only encrypted tokens via `_export_cookies()`

## NOTES
- A0 v1.5 enables API caching by default — `Cache-Control: no-store` is critical for correct UI state
- The `proxy.py` endpoint allows the WebUI to list open pages without exposing CDP port directly
- Screencast mode activates when noVNC port 6080 is unavailable
