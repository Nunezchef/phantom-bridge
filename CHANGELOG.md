# Changelog

## [1.1.1] - 2026-03-30

### Added
- **WebSocket push events** (`ws_broadcast.py`) — Bridge status and auth events are
  now pushed to the A0 UI in real time via Socket.IO using the A0 v1.5
  `ServerDeliveryEnvelope` format (`{handlerId, eventId, correlationId, ts, data}`).
  Eliminates the need to poll for bridge state changes.
- **Full test suite** — 106 tests across 7 files covering WS broadcast envelope shape,
  auth callbacks, system prompt routing, cache-control headers, Unicode sanitization,
  tool error messages, and task lifecycle.

### Changed
- **`webui/phantom-bridge-store.js`** — Replaced 5-second polling with WebSocket
  subscriptions (`phantom_bridge_status`, `phantom_bridge_auth`). Fallback poll
  interval extended to 30 seconds. On auth events, `export_cookies` is called before
  `fetchStatus()` so on-disk encrypted cookie files are always current (fixes P1
  reviewer comment).
- **`observer/manager.py`** — Added `_started` guard to make `start()` idempotent;
  `stop()` cancels and awaits all background tasks, clears the task list, and resets
  the flag. `_started = True` is now set only after `connect()` succeeds so a failed
  CDP connection leaves the manager in a retryable state (fixes P2 reviewer comment).
- **`extensions/system_prompt/_45_browser_bridge.py`** — Detects small/local models
  by name substring or context window ≤ 8192 and injects a compact ~200-token block
  instead of the full prompt. Both variants include canonical JSON tool-call examples
  for A0 v1.5 self-correction. Dynamic sections capped (5 playbooks, 3 sitemaps).
- **`api/bridge.py`** — Added `Cache-Control: no-store` on all responses to opt out
  of A0 v1.5 API/WS caching. Added `from __future__ import annotations` for Python
  3.9 compatibility.
- **`observer/sitemap_learner.py` / `observer/playbook_recorder.py`** — Page titles
  and DOM event strings are run through `_safe_str()` (UTF-8 round-trip with
  `errors='replace'`) before storage to prevent lone Unicode surrogates from crashing
  `json.dumps`.
- **`tools/bridge_record.py` / `tools/bridge_replay.py`** — All error responses now
  include canonical JSON call examples so A0 v1.5 agents can self-correct malformed
  tool invocations without human intervention. `break_loop=False` on all error paths.

## [1.1.0] - 2026-03-30

### Added
- **Cookie encryption at rest** — Cookie values are now encrypted using Fernet symmetric encryption before being written to disk. The encryption key is auto-generated at `data/.cookie_key` on first use. Cookie names and metadata remain in plaintext for structure inspection. Closes #3.
- **Per-domain cookie storage** — Cookies are now stored as individual files per domain at `data/cookies/<domain>.json` instead of a single monolithic `data/cookies.json`. A0 only loads cookies for the domain it needs, reducing token costs.
- **`bridge_decrypt_cookies` tool** — New A0 tool for on-demand cookie decryption. Returns plaintext cookie values in memory (never writes them to disk). Provides a ready-to-use `Cookie:` header string for HTTP requests.
- **`cryptography` dependency** — Added `cryptography>=42.0,<45.0` to requirements.txt for Fernet encryption support.

### Changed
- `api/bridge.py` — Cookie export, read, and delete operations now use encrypted per-domain files via `cookie_crypt` module.
- System prompt extension now teaches A0 about encrypted cookie storage and the `bridge_decrypt_cookies` tool.
- Updated README with new cookie management documentation, security details, and tool reference.

## [1.0.0] - 2026-03-28

Initial release.

- Remote browser control via noVNC (Xvfb + x11vnc + websockify)
- Session inheritance via shared Chromium profile directory
- Three-tier CDP observer system (auth registry, sitemap learner, playbook recorder)
- A0 system prompt injection with live session state
- WebUI sidebar panel with status, cookies, sitemaps, and playbooks
- 8 A0 tools for bridge management, auth queries, and workflow replay
