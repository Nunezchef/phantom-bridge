"""Bridge API handler — start/stop bridge, observer data queries."""

import json
import urllib.request
from pathlib import Path
from helpers.api import ApiHandler, Request, Response

_plugin_root = Path(__file__).resolve().parent.parent


class BridgeHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "status")

        if action == "status":
            return self._status()
        elif action == "start":
            return await self._start(input)
        elif action == "stop":
            return await self._stop()
        elif action == "auth_registry":
            return self._get_auth_registry()
        elif action == "sitemaps":
            return self._get_sitemaps()
        elif action == "playbooks":
            return self._get_playbooks()
        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    def _status(self) -> dict:
        from usr.plugins.phantom_bridge.bridge import get_bridge
        bridge = get_bridge()
        if bridge and bridge.is_running():
            status = bridge.status()
            return {"ok": True, "running": True, **status}
        return {"ok": True, "running": False}

    async def _start(self, input: dict) -> dict:
        from usr.plugins.phantom_bridge.bridge import get_bridge, create_bridge_from_config
        bridge = get_bridge()
        if bridge and bridge.is_running():
            return {"ok": True, "running": True, "message": "Already running", **bridge.status()}

        config = input.get("config", {})
        bridge = create_bridge_from_config(config)
        try:
            status = await bridge.start()
            return {"ok": True, "running": True, **status}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _stop(self) -> dict:
        from usr.plugins.phantom_bridge.bridge import get_bridge
        bridge = get_bridge()
        if not bridge or not bridge.is_running():
            return {"ok": True, "running": False, "message": "Not running"}
        result = await bridge.stop()
        return {"ok": True, **result}

    def _get_auth_registry(self) -> dict:
        auth_file = _plugin_root / "data" / "auth_registry.json"
        if auth_file.exists():
            try:
                registry = json.loads(auth_file.read_text())
                return {"ok": True, "registry": registry}
            except Exception:
                pass
        return {"ok": True, "registry": {}}

    def _get_sitemaps(self) -> dict:
        sitemaps_dir = _plugin_root / "data" / "sitemaps"
        result = {}
        if sitemaps_dir.exists():
            for f in sitemaps_dir.glob("*.json"):
                try:
                    result[f.stem] = json.loads(f.read_text())
                except Exception:
                    pass
        return {"ok": True, "sitemaps": result}

    def _get_playbooks(self) -> dict:
        playbooks_dir = _plugin_root / "data" / "playbooks"
        result = []
        if playbooks_dir.exists():
            for f in playbooks_dir.glob("*.json"):
                try:
                    pb = json.loads(f.read_text())
                    result.append({
                        "name": pb.get("name", f.stem),
                        "domain": pb.get("domain", ""),
                        "steps": len(pb.get("steps", [])),
                        "recorded_at": pb.get("recorded_at", ""),
                    })
                except Exception:
                    pass
        return {"ok": True, "playbooks": result}
