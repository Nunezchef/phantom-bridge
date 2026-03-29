# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Phantom Bridge is an **Agent Zero (A0) plugin** that opens a remote browser viewer (noVNC) so users can authenticate to any web service from their own browser. A0 inherits those sessions, learns site patterns, and can replay recorded workflows autonomously. The display layer uses noVNC (Xvfb + x11vnc + websockify), while the observation layer uses CDP (Chrome DevTools Protocol) for auth detection, sitemap learning, and playbook recording.

## Tech Stack
- Language: Python 3.10+
- Framework: Agent Zero plugin system (`helpers.tool.Tool`, `helpers.api.ApiHandler`, `helpers.extension.Extension`)
- Package Manager: pip
- Test Framework: none
- Build Tool: none (plugin is copied into A0's `usr/plugins/`)
- Linter: none
- Frontend: Alpine.js (via A0's built-in Alpine)
- Runtime dependency: `websockets>=12.0,<14.0`
- System dependency: `x11vnc`, `novnc` (apt packages — installed via execute.py)
- Optional dependency: `pyyaml` (config loading)

## Directory Structure
```
bridge.py              # Core BrowserBridge singleton — Chromium lifecycle
default_config.yaml    # Plugin defaults (port, profile dir, headless, etc.)
plugin.yaml            # A0 plugin registration (name: phantom_bridge, v0.2.0)
requirements.txt       # websockets dependency
observer/              # Three-tier CDP observation system
  cdp_client.py        #   WebSocket client with pub/sub + auto-reconnect
  auth_registry.py     #   L1: cookie-based auth detection per domain
  sitemap_learner.py   #   L2: URL pattern learning per domain
  playbook_recorder.py #   L3: replayable navigation sequence recording
  manager.py           #   Orchestrates all observer layers
tools/                 # A0 tool implementations (one tool per file)
  bridge_open.py       #   Start bridge → returns connect URL
  bridge_close.py      #   Stop bridge (sessions persist)
  bridge_status.py     #   Bridge status, pages, domains
  bridge_auth.py       #   Query auth registry
  bridge_sitemap.py    #   Query learned sitemaps
  bridge_record.py     #   Start/stop playbook recording
  bridge_replay.py     #   Replay saved playbooks
  bridge_health.py     #   Check session health
api/                   # HTTP API handlers for webui
  bridge.py            #   Start/stop/status/auth/sitemaps/playbooks
  proxy.py             #   CDP page list proxy
extensions/            # A0 extension hooks
  system_prompt/       #   _45_ prefix = load order 45
  python/message_loop_start/  # _30_ prefix = load order 30
webui/                 # Alpine.js sidebar panel for A0's UI
  main.html            #   Plugin panel (modal content)
  phantom-bridge-store.js  # Alpine store — polls API every 5s
  bridge.html          #   noVNC iframe embed (remote browser viewer)
execute.py             # Dependency installer (x11vnc + novnc)
hooks.py               # A0 framework lifecycle hooks (install)
data/                  # Persistent state (gitignored, created at runtime)
```

## Conventions
- Naming: snake_case for files and functions, PascalCase for classes
- Imports: `from __future__ import annotations` at top of every module; A0 framework imports are deferred inside methods to avoid circular imports
- Error handling: try/except with logging.warning for non-critical failures; RuntimeError for critical failures
- Observer pattern: CDP events dispatched via `CDPClient.subscribe()` callbacks (sync or async)
- Tool pattern: each tool extends `helpers.tool.Tool`, implements `async execute(**kwargs) -> Response`
- API pattern: each handler extends `helpers.api.ApiHandler`, implements `async process(input, request) -> dict`
- Config loading: every tool/extension has a `_load_config()` method that tries `helpers.plugins.get_plugin_config()` first, falls back to reading `default_config.yaml` directly

## Commands
- Install: `pip install -r requirements.txt`
- Dev: copy plugin to A0's `usr/plugins/phantom_bridge/` and restart A0
- Test: none configured
- Lint: none configured

## Key Patterns

- **Singleton bridge**: `_bridge` module-level variable in `bridge.py`; only one Chromium process per container
- **noVNC display layer**: bridge.py manages three processes — Chromium + x11vnc + websockify. noVNC serves on port 6080 (configurable). Display and observation are separate concerns.
- **A0 plugin imports**: use `from usr.plugins.phantom_bridge.module import X` — no sys.path hacks
- **Config cascade**: `default_config.yaml` -> A0 plugin settings UI -> tool call params
- **Profile sharing**: The critical integration — `_30_browser_bridge_profile.py` monkeypatches `browser_agent.State.get_user_data_dir()` to return the bridge's persistent profile at `data/profile/`. Also patches `__del__` to prevent profile deletion.
- **Observer data files**: `data/auth_registry.json`, `data/sitemaps/*.json`, `data/playbooks/*.json`
- **Extension load order**: `_30_` and `_45_` numeric prefixes in filenames control A0's extension execution order
- **WebUI API polling**: Alpine store polls `/plugins/phantom_bridge/bridge` every 10 seconds for live state
- **CDP reconnect**: `CDPClient` has exponential backoff reconnection (0.5s initial, 5s max, 10 attempts)
- **Deferred imports**: Tools and extensions import from `bridge.py` and `observer/` inside method bodies to avoid import-time errors when running outside A0

## Key Files
- Entry point: `bridge.py` (BrowserBridge class + factory)
- Config: `default_config.yaml`, `plugin.yaml`
- Observer core: `observer/cdp_client.py`, `observer/manager.py`
- Auth detection: `observer/auth_registry.py` (cookie diffing + auth URL pattern matching)
- Profile patch: `extensions/python/message_loop_start/_30_browser_bridge_profile.py`
- System prompt injection: `extensions/system_prompt/_45_browser_bridge.py`
- WebUI store: `webui/phantom-bridge-store.js`
