# Phantom Bridge

![Phantom Bridge banner](docs/icon.png)

**Log into any service once. A0 uses it forever.**

An Agent Zero plugin that opens a remote browser viewer so you can authenticate to any web service from your own browser. A0 inherits those sessions, learns site patterns, and can replay recorded workflows autonomously.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![A0 Compatible](https://img.shields.io/badge/Agent_Zero-plugin-orange.svg)](https://github.com/frdel/agent-zero)

## How It Works

1. Tell A0: *"open the browser bridge"*
2. Open the remote viewer from A0's sidebar (Phantom Bridge panel)
3. You see the container's Chromium — log into anything (Google, X, NotebookLM, Toast, etc.)
4. Close the bridge. A0's browser agent inherits every session.
5. Show A0 a workflow once — it can replay it forever.

No cookie hacking, no API keys, no OAuth apps. The browser is real, the sessions are real.

## Architecture

```
Your Browser ──→ A0 Web UI ──→ Phantom Bridge Panel
                                    │
                           noVNC (remote viewer)
                                    │
                        ┌───────────┴───────────┐
                        │  Container Chromium    │
                        │  (Xvfb + x11vnc)      │
                        │                        │
                        │  CDP Observer Layers:  │
                        │  · Auth Registry       │
                        │  · Sitemap Learner     │
                        │  · Playbook Recorder   │
                        │                        │
                        │  Persistent Profile:   │
                        │  data/profile/         │
                        └────────────────────────┘
```

## Setup

### 1. Install the plugin

Copy into A0's `usr/plugins/`:

```bash
cp -r phantom_bridge /path/to/a0/usr/plugins/
```

### 2. Install dependencies

From A0's Plugins UI, click the Execute button on Phantom Bridge. Or manually:

```bash
apt-get install -y x11vnc novnc
pip install websockets
```

### 3. Expose ports in docker-compose

```yaml
services:
  agent-zero:
    ports:
      - "5050:5000"
      - "6080:6080"    # Phantom Bridge (noVNC)
```

## Usage

### Via A0 Chat

Just talk to A0:

- *"Open the browser bridge"*
- *"I need to log into Google"*
- *"Record this workflow"* → demonstrate it → *"Replay it every morning"*

A0 knows when to suggest the bridge. If it can't access a service because authentication is needed, it will ask you to open the bridge.

### Pattern Learning

1. Open the bridge and tell A0: *"Record this — I'll show you how to generate images on Gemini"*
2. Walk through the workflow in the remote viewer
3. Tell A0: *"Stop recording"*
4. From now on: *"Generate images on Gemini like I showed you"* — A0 replays it autonomously.

### Tools

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

## Configuration

Edit `default_config.yaml` or configure via A0's plugin settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable the plugin |
| `remote_debug_port` | `9222` | CDP port (internal) |
| `novnc_port` | `6080` | Remote viewer port |
| `profile_dir` | `data/profile` | Browser profile location |
| `headless` | `true` | Headless mode (noVNC works either way) |

## Security

- **Port 6080 gives full browser control.** Only expose on trusted networks.
- **The profile directory contains cookies and session tokens.** Treat as sensitive.
- Use Docker's network isolation to restrict access.

## License

MIT
