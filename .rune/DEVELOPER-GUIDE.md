# Developer Guide: Phantom Bridge

## What This Does
An Agent Zero plugin that lets users log into any web service via the container's Chromium browser (exposed over CDP port 9222), so A0's browser agent inherits those authenticated sessions automatically. Observer layers passively learn auth patterns, site maps, and replayable workflows.

## Quick Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Deploy to Agent Zero
cp -r . /path/to/a0/usr/plugins/phantom_bridge/

# Expose CDP port in docker-compose.yml
# ports:
#   - "9222:9222"

# Restart A0 — the plugin loads automatically via plugin.yaml
```

## Key Files
- `bridge.py` — Core BrowserBridge class, Chromium process management, singleton factory
- `observer/cdp_client.py` — CDP WebSocket client shared by all observer layers
- `observer/auth_registry.py` — Detects authenticated domains by diffing cookies before/after navigation
- `observer/manager.py` — Starts/stops all observer layers with a shared CDP connection
- `tools/bridge_open.py` — The main tool A0 calls to launch the bridge
- `extensions/python/message_loop_start/_30_browser_bridge_profile.py` — Monkeypatches A0's browser agent to share the bridge's profile directory
- `extensions/system_prompt/_45_browser_bridge.py` — Injects live observer state into A0's system prompt
- `webui/main.html` — Sidebar panel UI (Alpine.js)
- `default_config.yaml` — All configurable settings with defaults

## How to Contribute
1. Fork or branch from main
2. Make changes — the plugin has no test suite yet, so test manually against a running A0 instance
3. Open a PR — describe what and why

## Common Issues
- **`websockets` not installed** — Run: `pip install -r requirements.txt`
- **No Chromium binary found** — Inside the A0 container, run: `playwright install chromium`
- **Port 9222 not accessible** — Ensure the port is mapped in `docker-compose.yml` (`"9222:9222"`)
- **Profile not shared** — The `_30_browser_bridge_profile.py` extension must load before any browser_agent invocation; check A0 logs for "browser_bridge: patched browser_agent"
