<p align="center">
  <img src="docs/banner.png" alt="Phantom Bridge" width="700" />
</p>

<p align="center">
  <strong>Log into any service once. A0 uses it forever.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"></a>
  <a href="https://github.com/frdel/agent-zero"><img src="https://img.shields.io/badge/Agent_Zero-plugin-orange.svg" alt="A0 Compatible"></a>
  <a href="#"><img src="https://img.shields.io/badge/version-1.0.0-purple.svg" alt="Version 1.0.0"></a>
</p>

<p align="center">
  An Agent Zero plugin that opens a remote browser so you can authenticate to any web service from your own browser.<br>
  A0 inherits those sessions, learns site patterns, and replays recorded workflows autonomously.
</p>

---

## The Problem

A0 runs inside a Docker container with its own Chromium. When it needs to access authenticated services, the traditional options are:

- **Export cookies** from your host browser → import into the container → watch them get invalidated because fingerprints don't match
- **Build OAuth integrations** for every service → weeks of work, partner approvals, API waitlists
- **Hard-code credentials** → security nightmare, breaks on 2FA

None of these scale. Every new service is another integration project.

## The Solution

Phantom Bridge flips the model. Instead of moving credentials *into* the container, you use the container's browser *directly*:

```
1. Tell A0: "open the browser bridge"
2. A remote browser viewer appears — you're looking at A0's Chromium
3. Log into anything. Google, NotebookLM, X, Threads, Toast, OpenTable.
4. Close the bridge. A0's browser agent inherits every session.
5. Show A0 a workflow once — it replays it forever.
```

Sessions persist across container restarts. No export/import. No fingerprint mismatch. No API keys.

---

## Features

### Remote Browser Control

Full native browser control via [noVNC](https://novnc.com) — not screenshots, not iframes, real VNC.

- **Keyboard, mouse, clipboard** — everything works, including captchas
- **Draggable modal** inside A0's UI with minimize, resize, and pop-out
- **Screencast fallback** — works through A0's port when noVNC port isn't exposed

### Session Inheritance

The bridge and A0's `browser_agent` share the same Chromium profile directory. When you log into Google via the bridge, A0's browser agent has those cookies immediately. No transfer step.

```
Bridge Chromium ──→ data/profile/ ←── A0's browser_agent
                   (shared cookies, localStorage, sessions)
```

### Cookie Management

All cookies are exported to `data/cookies.json` in a clean, readable format — grouped by domain with full metadata:

```json
{
  "google.com": [
    { "name": "SID", "value": "...", "domain": ".google.com", "httpOnly": true, "secure": true, "expires": 1756684800 },
    { "name": "HSID", "value": "...", "domain": ".google.com", "httpOnly": true, "secure": false }
  ],
  "x.com": [
    { "name": "auth_token", "value": "...", "domain": ".x.com", "httpOnly": true, "secure": true }
  ]
}
```

- Live cookie counts per domain in the sidebar panel
- **Delete All** button to wipe every session instantly
- A0 can read `cookies.json` for any purpose — HTTP clients, API calls, automation scripts

### Intelligent Observer

Three observation layers watch silently while you browse:

| Layer | What it does | Data file |
|-------|-------------|-----------|
| **Auth Registry** | Detects logins via cookie diffing + auth URL patterns | `data/auth_registry.json` |
| **Sitemap Learner** | Maps URL patterns and features per domain | `data/sitemaps/*.json` |
| **Playbook Recorder** | Records replayable navigation sequences | `data/playbooks/*.json` |

### A0 Intelligence Layer

The plugin injects context into A0's system prompt (additive — never replaces the core prompt):

- **When to suggest the bridge** — A0 proactively suggests opening the bridge when it detects authentication failures, login redirects, or requests for authenticated services
- **Live session state** — A0 knows which domains are authenticated and when sessions expire
- **Playbook awareness** — A0 knows what workflows have been recorded and suggests replay when appropriate

```
"I need authenticated access to NotebookLM. Would you like to
open the Phantom Bridge so you can log in? I'll be able to use
that session afterward."
```

### Pattern Learning

Teach A0 once, it does it forever:

1. Open the bridge
2. Tell A0: *"Record this — I'll show you how to generate images on Gemini"*
3. Walk through the workflow in the remote viewer
4. Tell A0: *"Stop recording"*
5. From now on: *"Generate images on Gemini like I showed you"*

A0 replays the recorded workflow autonomously using Playwright with the shared browser profile.

---

## Architecture

```
Your Browser ──→ A0 Web UI (:5050)
                    │
                    ├── Sidebar Panel ── status, cookies, sitemaps, playbooks
                    │
                    └── Phantom Bridge Modal (draggable, resizable)
                            │
                      noVNC iframe (:6080)
                            │
                      websockify ──→ x11vnc ──→ Xvfb display
                                                    │
                                               Chromium (system)
                                                    │
                                              CDP WebSocket
                                                    │
                                        ┌───────────┴───────────┐
                                        │    Observer Layers     │
                                        │  ┌─ Auth Registry      │
                                        │  ├─ Sitemap Learner    │
                                        │  └─ Playbook Recorder  │
                                        └────────────────────────┘
                                                    │
                                          data/profile/ (shared)
                                                    │
                                          A0's browser_agent
```

### How Profile Sharing Works

The `_30_browser_bridge_profile.py` extension runs at `message_loop_start` and patches `browser_agent.State.get_user_data_dir()` to return the bridge's profile directory instead of an ephemeral one. It also patches `__del__` to prevent profile deletion. This means A0's browser agent uses the exact same cookies, localStorage, and sessions you created via the bridge.

---

## Setup

### 1. Install the plugin

```bash
# Copy into A0's plugin directory
cp -r phantom_bridge /path/to/a0/usr/plugins/

# Or clone directly
git clone https://github.com/Nunezchef/phantom-bridge.git /path/to/a0/usr/plugins/phantom_bridge
```

### 2. Install dependencies

From A0's Plugins UI, click **Execute** on Phantom Bridge. Or run manually:

```bash
docker exec -it a0 python /a0/usr/plugins/phantom_bridge/execute.py
```

This installs: `x11vnc`, `novnc`, `xvfb`, `xdotool`, `chromium`

### 3. Expose the viewer port

Add one line to your `docker-compose.yml`:

```yaml
services:
  agent-zero:
    ports:
      - "5050:5000"
      - "6080:6080"    # Phantom Bridge remote viewer
```

Then restart: `docker compose up -d`

> **Note:** If you can't change docker-compose, the plugin still works — it falls back to a screencast mode that streams through A0's existing port. No extra ports needed.

### 4. Use it

Just talk to A0:

- *"Open the browser bridge"*
- *"I need to log into Google"*
- *"Record this workflow"*
- *"Replay the export I showed you"*

Or click the phantom icon in A0's chat bar.

---

## Tools

| Tool | Description |
|------|-------------|
| `browser_bridge_open` | Start the bridge + remote viewer |
| `browser_bridge_close` | Stop the bridge (sessions persist) |
| `browser_bridge_status` | Check status, pages, authenticated domains |
| `bridge_auth` | Query authenticated domains + session expiry |
| `bridge_health` | Test if a session is still valid |
| `bridge_sitemap` | Learned URL patterns per domain |
| `bridge_record` | Start/stop recording a workflow |
| `bridge_replay` | Replay a saved workflow autonomously |

---

## Configuration

Edit `default_config.yaml` or configure via A0's plugin settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable the plugin |
| `remote_debug_port` | `9222` | CDP port (internal) |
| `novnc_port` | `6080` | Remote viewer port |
| `profile_dir` | `data/profile` | Browser profile location |
| `headless` | `false` | Set `true` to disable display rendering |
| `window_width` | `1280` | Browser viewport width |
| `window_height` | `900` | Browser viewport height |

---

## Data Storage

All persistent data lives in `data/` (survives container restarts when `/usr` is volume-mounted):

```
data/
├── profile/              # Chromium user data (cookies, localStorage, sessions)
├── cookies.json          # Exported cookies — grouped by domain, readable JSON
├── auth_registry.json    # Authenticated domains with expiry metadata
├── sitemaps/             # Learned URL patterns per domain
└── playbooks/            # Recorded workflows for autonomous replay
```

### Security

- **Cookies are sensitive data.** The `data/` directory contains session tokens. Treat it like you would a password vault.
- **Port 6080 gives full browser control.** Only expose on trusted networks.
- **The profile directory is gitignored.** Never commit it.
- All cookie data stays inside the container. Nothing is sent externally.

---

## Use Cases

| Service | What A0 Can Do After You Log In |
|---------|-------------------------------|
| **Google** | Access Gmail, Drive, Calendar, any Google service |
| **NotebookLM** | Query knowledge bases, generate content |
| **X / Twitter** | Post content, monitor mentions, engage |
| **Threads** | Publish posts, read feeds |
| **Toast POS** | Pull sales data, sync menus, export reports |
| **OpenTable** | Manage reservations, respond to reviews |
| **DoorDash / Uber Eats** | Accept orders, update menus |
| **Bank portals** | Read-only financial data for reporting |
| **Any web app** | If you can log into it, A0 can use it |

---

## How It Compares

| Approach | Setup | Captchas | Session Persistence | Fingerprint Match |
|----------|-------|----------|--------------------|--------------------|
| Cookie export/import | Manual | Fails | Fragile | No |
| OAuth integration | Weeks per service | N/A | Depends | N/A |
| Credential injection | Security risk | Fails on 2FA | Fragile | No |
| **Phantom Bridge** | **5 minutes** | **Works** | **Persistent** | **Perfect** |

---

## Plugin Structure

```
phantom_bridge/
├── plugin.yaml            # A0 plugin manifest
├── bridge.py              # Core BrowserBridge singleton — Chromium + noVNC lifecycle
├── screencast.py           # CDP screencast manager (zero-config fallback)
├── execute.py             # Dependency installer
├── hooks.py               # A0 framework lifecycle hooks
├── default_config.yaml    # Plugin defaults
├── observer/              # Three-tier CDP observation system
│   ├── cdp_client.py      # WebSocket client with pub/sub + auto-reconnect
│   ├── auth_registry.py   # L1: cookie-based auth detection
│   ├── sitemap_learner.py # L2: URL pattern learning
│   ├── playbook_recorder.py # L3: workflow recording
│   └── manager.py         # Orchestrates all observer layers
├── tools/                 # A0 tool implementations (one per file)
├── api/                   # HTTP API handlers
├── extensions/            # A0 extension hooks
│   ├── system_prompt/     # Injects bridge awareness into A0's prompt
│   ├── python/            # Profile sharing patch
│   ├── prompts/           # Tool usage examples for A0
│   └── webui/             # Chat bar button + modal injection
└── webui/                 # Alpine.js sidebar panel + bridge viewer
```

---

## License

MIT

---

<p align="center">
  <sub>Built for <a href="https://github.com/frdel/agent-zero">Agent Zero</a> by <a href="https://github.com/Nunezchef">@Nunezchef</a></sub>
</p>
