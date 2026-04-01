"""
Browser Bridge — Profile sharing extension.

Patches A0's browser_agent State class to use the Browser Bridge's
persistent profile directory instead of an ephemeral per-agent one.
This ensures that when the user logs into Google (etc.) via the bridge,
the browser_agent tool picks up those cookies and sessions.

Runs at message_loop_start so the patch is in place before any
browser_agent invocations.
"""

from __future__ import annotations

import logging
from pathlib import Path

from helpers.extension import Extension

logger = logging.getLogger("browser_bridge")

_patched = False


class BrowserBridgeProfilePatch(Extension):
    async def execute(self, loop_data=None, **kwargs):
        global _patched
        if _patched:
            return

        # Load config to check if enabled
        config = self._load_config()
        if not config.get("enabled", True):
            return

        # Determine the shared profile directory
        from usr.plugins.phantom_bridge.data_paths import get_profile_dir

        shared_profile = get_profile_dir()

        # Patch the browser_agent State class
        try:
            from plugins._browser_agent.tools.browser_agent import State

            original_get_user_data_dir = State.get_user_data_dir

            def patched_get_user_data_dir(self_state):
                """Return the shared bridge profile directory instead of
                an ephemeral per-agent directory."""
                return str(shared_profile)

            State.get_user_data_dir = patched_get_user_data_dir
            _patched = True

            logger.info(
                "browser_bridge: patched browser_agent to use shared profile at %s",
                shared_profile,
            )

            # Also patch __del__ to NOT delete the shared profile
            original_del = State.__del__

            def patched_del(self_state):
                """Clean up without deleting the shared profile directory."""
                self_state.kill_task()
                # Skip files.delete_dir — we want the profile to persist

            State.__del__ = patched_del
            logger.info(
                "browser_bridge: patched State.__del__ to preserve shared profile"
            )

        except ImportError as e:
            logger.warning(
                "browser_bridge: could not patch browser_agent (not found): %s", e
            )
        except Exception as e:
            logger.warning("browser_bridge: could not patch browser_agent: %s", e)

    def _load_config(self) -> dict:
        """Load plugin configuration."""
        try:
            from helpers.plugins import get_plugin_config

            return get_plugin_config("phantom_bridge", agent=self.agent) or {}
        except ImportError:
            pass

        try:
            import yaml

            config_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "default_config.yaml"
            )
            if config_path.exists():
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
        except ImportError:
            pass

        return {}
