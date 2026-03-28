# Browser Bridge

<!-- Add banner image here -->
![Browser Bridge banner](docs/banner.png)

**Log into any service once. A0 uses it forever.**

An Agent Zero plugin that exposes the container's Chromium browser to the host machine via Chrome DevTools Protocol. You connect from your regular browser, log into any service — Google, Toast, OpenTable, X, whatever — and A0's browser agent inherits those authenticated sessions. No cookie hacks, no API keys, no OAuth apps.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![A0 Compatible](https://img.shields.io/badge/Agent_Zero-plugin-orange.svg)](https://github.com/frdel/agent-zero)

## The Problem

A0 runs inside a Docker container with its own Chromium. When A0's browser agent needs to access authenticated services, the traditional approach is:

1. Export cookies from your host browser
2. Import them into the container
3. Watch it fail because browser fingerprints don't match
4. Google/Twitter/etc. invalidate the session
5. Repeat

Or build OAuth integrations for every service — weeks of work each, partner approvals, API waitlists.

## The Solution

Browser Bridge flips the model. Instead of moving credentials *into* the container, you use the container's browser *directly*:

1. Tell A0: "open the browser bridge"
2. Open `http://localhost:9222` in your Chrome
3. You're now looking at the container's Chromium
4. Log into anything — the fingerprint matches because it *is* the container's browser
5. Close the bridge. A0's browser agent inherits every session.

Sessions persist across container restarts. No export/import. No fingerprint mismatch. No API keys.

## Use Cases

| Service | What A0 Can Do After You Log In |
|---------|-------------------------------|
| **Toast POS** | Pull sales data, sync menus, export reports |
| **OpenTable** | Manage reservations, respond to reviews |
| **Square** | Payment data, inventory sync |
| **Google Business** | Update hours, respond to reviews, upload photos |
| **DoorDash / Uber Eats** | Accept orders, update menus, check payouts |
| **7shifts** | Staff scheduling, shift swaps |
| **NotebookLM** | Query knowledge bases for SOPs, training docs |
| **X / Twitter** | Post content, monitor mentions |
| **Threads** | Content publishing |
| **Bank portals** | Read-only financial data for P&L reporting |
| **Any web app** | If you can log into it, A0 can use it |

## Architecture

```
Host Machine                          Docker Container
+-------------------+                +--------------------------------+
| Your Chrome       |   CDP (9222)   | Chromium (Playwright)          |
| Opens localhost:  | ────────────>  | --remote-debugging-port=9222   |
| 9222 to control   |                |                                |
| container browser |                | Persistent profile at:         |
+-------------------+                | plugins/browser_bridge/data/   |
                                     |   profile/                     |
                                     |                                |
                                     | A0's browser_agent uses the    |
                                     | SAME profile directory ───────>|── Sessions shared
                                     +--------------------------------+
```

## Setup

### 1. Expose port 9222 in docker-compose

```yaml
services:
  agent-zero:
    ports:
      - "5050:5000"
      - "9222:9222"    # Browser Bridge
```

### 2. Install the plugin

Copy the `browser_bridge/` directory into your A0's `usr/plugins/`:

```bash
cp -r browser_bridge /path/to/a0/usr/plugins/
```

A0 discovers it automatically through the plugin system.

### 3. (Optional) Install full Chromium

The bridge works best with a full (headed) Chromium binary. Inside the container:

```bash
playwright install chromium
```

If only the headless shell is available, the bridge will still work but some DevTools features may be limited.

## Usage

### Via A0 Chat

Just talk to A0:

- *"Open the browser bridge"*
- *"I need to log into Google"*
- *"Start the bridge so I can authenticate"*

A0 calls `browser_bridge_open` and gives you the connection URL.

### Step by Step

1. **Start**: Tell A0 to open the bridge
2. **Connect**: Open `http://localhost:9222` in your Chrome
3. **Click** the inspectable page link to see the container's browser
4. **Navigate** to any service and log in normally
5. **Close**: Tell A0 to close the bridge when done
6. **Done**: A0's browser agent now has your authenticated sessions

### Tools

| Tool | Description |
|------|-------------|
| `browser_bridge_open` | Launch Chromium with remote debugging. Returns connection URL |
| `browser_bridge_close` | Stop the bridge. Optional: `clear_profile=true` to wipe all sessions |
| `browser_bridge_status` | Check if bridge is running, list open pages and authenticated domains |

## How It Works

The plugin does two things:

1. **Bridge**: Launches Chromium with `--remote-debugging-port=9222` and a persistent user data directory. This is the browser you connect to from your host.

2. **Profile sharing**: A `message_loop_start` extension patches A0's `browser_agent.State.get_user_data_dir()` to return the bridge's profile directory instead of an ephemeral one. It also patches `__del__` to not delete the shared profile. This means A0's browser agent uses the exact same cookies, localStorage, and sessions you created via the bridge.

## Configuration

Edit `default_config.yaml` or configure via A0's plugin settings UI:

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable the plugin |
| `remote_debug_port` | `9222` | CDP port exposed to host |
| `profile_dir` | `data/profile` | Browser profile location (relative to plugin dir) |
| `headless` | `false` | Run headed for DevTools inspection |
| `window_width` | `1280` | Browser viewport width |
| `window_height` | `900` | Browser viewport height |
| `bind_address` | `0.0.0.0` | Listen address inside container |

## Security

- **Port 9222 gives full browser control.** Only expose on trusted networks.
- **Never expose 9222 to the internet** in production.
- **The profile directory contains cookies and session tokens.** Treat it as sensitive data.
- Use Docker's network isolation to restrict access to the debug port.

## License

MIT
