# OBSERVER MODULE

## OVERVIEW
Three-tier CDP observation system: auth detection → sitemap learning → playbook recording. Shares single CDP connection via `CDPClient`.

## STRUCTURE
```
observer/
├── cdp_client.py          # WebSocket CDP client with pub/sub + exponential backoff reconnect
├── manager.py             # Orchestrates lifecycle — shares one CDP connection across all layers
├── auth_registry.py       # L1: cookie diffing + auth URL pattern detection per domain
├── sitemap_learner.py     # L2: URL pattern mapping + feature discovery per domain
├── playbook_recorder.py   # L3: records replayable navigation sequences
└── playbook.py            # Standalone playbook runner (has __main__ block)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| CDP connection | `cdp_client.py` | `CDPClient.connect()`, `subscribe()`, `send()` |
| Start all observers | `manager.py` | `ObserverManager.start()` — idempotent |
| Auth detection logic | `auth_registry.py` | Cookie diffing on `Network.responseReceived` |
| URL pattern learning | `sitemap_learner.py` | Tracks visited URLs per domain |
| Playbook recording | `playbook_recorder.py` | Records step sequences for replay |
| Playbook execution | `playbook.py` | Standalone runner with `__main__` |

## CONVENTIONS
- **CDP pub/sub:** `CDPClient.subscribe(event_name, callback)` — callbacks can be sync or async
- **Domain enabling:** `CDPClient.enable_domains("Page", "Network", "Runtime")` before subscribing
- **Data files:** All persisted to `data/` — `auth_registry.json`, `sitemaps/*.json`, `playbooks/*.json`
- **Manager lifecycle:** `start()` connects CDP + enables domains + starts all observers; `stop()` cancels all background tasks

## ANTI-PATTERNS
- **DO NOT** start observers without CDP listener first — `send()` calls hang without `_listen()` running
- **DO NOT** create multiple CDP connections — manager shares one across all layers
- **DO NOT** call `start()` twice — it's idempotent but logs a warning

## NOTES
- Reconnect: exponential backoff (0.5s → 5s max, 10 attempts) in `cdp_client.py`
- `playbook.py` has a `__main__` block for standalone testing
- L2 (sitemap) and L3 (playbook) are optional — manager imports them conditionally
