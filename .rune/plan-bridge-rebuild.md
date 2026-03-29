# Feature: Phantom Bridge v2 — noVNC + Pattern Learning + Clean Install

## Overview
Major rebuild: replace screenshot viewer with noVNC, add A0 intelligence layer (additive system prompt, auto-suggest, playbook awareness), enable pattern learning from user demos, fix all A0 convention violations, clean installation.

## Phases
| # | Name | Status | Plan File | Summary |
|---|------|--------|-----------|---------|
| 1 | Clean + noVNC | ✅ Done | plan-bridge-rebuild-phase1.md | Delete dead code, fix imports, add noVNC launcher + viewer, execute.py |
| 2 | A0 Intelligence | ✅ Done | plan-bridge-rebuild-phase2.md | Rewrite system prompt (additive), auto-suggest on auth failure, playbook awareness |
| 3 | Pattern Learning | ✅ Done | (already wired) | Observer → playbook → system prompt → replay. End-to-end pipeline complete. |
| 4 | Polish | ✅ Done | plan-bridge-rebuild-phase4.md | README, plugin.yaml v1.0.0, CLAUDE.md, clean file structure |

## Key Decisions
- **noVNC via apt** (x11vnc + novnc packages): stable, single port 6080, iframe-embeddable
- **Additive system prompt**: extension APPENDS to A0's prompt, never replaces core
- **execute.py for deps**: user runs from Plugins UI to install x11vnc + novnc
- **Proper imports**: `from usr.plugins.phantom_bridge.module import X` — no sys.path hacks
- **A0 notification system**: toasts, not inline error divs
- **Store Gate pattern**: already correct in main.html, new bridge.html must follow

## Convention Fixes Required (from A0 plugin audit)
- Import paths: remove all `sys.path` hacks, use `usr.plugins.phantom_bridge.*`
- Add `execute.py` (dependency installer) and `hooks.py` (install hook)
- Add `webui/config.html` (settings UI — declared external but missing)
- Use A0 notifications instead of console.error
- Remove files outside standard layout (projecticon.png, webicon.png at root)

## Architecture
```
A0 Web UI (:5050)
  ├── Sidebar panel (main.html) — status, auth, playbooks
  └── Bridge viewer (bridge.html) → iframe → noVNC (:6080)
                                        ↓ WebSocket
                                    websockify → x11vnc → Xvfb:DISPLAY
                                                            ↑
                                                        Chromium (bridge.py)
                                                            ↑ CDP
                                                        Observers (auth, sitemap, playbook)
```

## Files to DELETE
- `api/click.py` — replaced by noVNC native input
- `api/keyboard.py` — replaced by noVNC native input

## Files to ADD
- `execute.py` — installs x11vnc + novnc apt packages
- `hooks.py` — install hook calls execute.py
- `webui/config.html` — plugin settings UI

## Files to REWRITE
- `webui/bridge.html` — noVNC iframe embed (replaces screenshot viewer)
- `api/proxy.py` — remove screenshot/navigate/reload/go_back, keep only pages + bridge status
- `extensions/system_prompt/_45_browser_bridge.py` — full intelligence layer
- `bridge.py` — add noVNC process management (x11vnc + websockify)
