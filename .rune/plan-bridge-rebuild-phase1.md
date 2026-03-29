# Phase 1: Clean Sweep + noVNC Integration

## Goal
Delete all dead screenshot/click/keyboard code. Add noVNC process management to bridge.py. Create new bridge.html as noVNC iframe embed. Add execute.py for dependency installation. Fix import paths.

## Data Flow
```
bridge.start() → launch Chromium → launch x11vnc (captures DISPLAY) → launch websockify (:6080 → :5900)
                                                                            ↓
bridge.html → iframe src="/vnc.html?autoconnect=true&resize=scale" (:6080)
```

## Tasks

### Wave 1 — Delete dead code
- [ ] Delete `api/click.py`
- [ ] Delete `api/keyboard.py`
- [ ] Strip `api/proxy.py` down to only: pages list + bridge status (remove screenshot, navigate, reload, go_back, _recv_response, _find_ws_url)
- [ ] Fix `api/proxy.py` imports: use `from usr.plugins.phantom_bridge.bridge import ...` not sys.path hack
- [ ] Fix `api/bridge.py` imports: same

### Wave 2 — noVNC process management in bridge.py
- [ ] Add x11vnc + websockify process launching to `BrowserBridge.start()`
- [ ] Add process cleanup to `BrowserBridge.stop()`
- [ ] Add `novnc_port` config (default 6080)
- [ ] Detect DISPLAY env var (default :99)
- [ ] Add noVNC status to `BrowserBridge.status()` return dict
- [ ] Update `default_config.yaml` with novnc_port

### Wave 3 — New bridge.html + execute.py
- [ ] Rewrite `webui/bridge.html` as noVNC iframe embed with Store Gate
- [ ] Update `webui/phantom-bridge-store.js` — remove screenshot polling, add noVNC URL
- [ ] Create `execute.py` — installs x11vnc + novnc via apt
- [ ] Create `hooks.py` — install hook

## Acceptance Criteria
- [ ] `api/click.py` and `api/keyboard.py` deleted
- [ ] `api/proxy.py` has no screenshot/navigate/keyboard code
- [ ] bridge.py starts x11vnc + websockify alongside Chromium
- [ ] bridge.html loads noVNC in iframe
- [ ] execute.py installs dependencies cleanly
- [ ] No sys.path hacks in any file
