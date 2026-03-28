"""
bridge_record — A0 tool to start/stop recording and manage playbooks.

Records user browser actions as replayable playbooks via CDP observation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from python.helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeRecord(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        action = self.args.get("action", "").lower()
        name = self.args.get("name", "")
        description = self.args.get("description", "")

        if action not in ("start", "stop", "list", "delete"):
            return Response(
                message=(
                    "Invalid action. Use one of: start, stop, list, delete.\n"
                    '  start — begin recording (requires "name")\n'
                    "  stop  — stop recording and save playbook\n"
                    "  list  — list all saved playbooks\n"
                    '  delete — delete a playbook (requires "name")'
                ),
                break_loop=False,
            )

        recorder = self._get_recorder()
        if recorder is None:
            return Response(
                message=(
                    "Playbook recorder is not available. "
                    "The browser bridge must be running with CDP observer enabled."
                ),
                break_loop=False,
            )

        if action == "start":
            return await self._start_recording(recorder, name)
        elif action == "stop":
            return await self._stop_recording(recorder, description)
        elif action == "list":
            return self._list_playbooks(recorder)
        elif action == "delete":
            return self._delete_playbook(recorder, name)

        # unreachable
        return Response(message="Unknown action.", break_loop=False)

    async def _start_recording(self, recorder: Any, name: str) -> Response:
        if not name:
            return Response(
                message='A "name" argument is required to start recording.',
                break_loop=False,
            )
        try:
            await recorder.start_recording(name)
        except RuntimeError as e:
            return Response(message=f"Cannot start recording: {e}", break_loop=False)
        except ValueError as e:
            return Response(message=f"Invalid name: {e}", break_loop=False)

        return Response(
            message=(
                f"Recording started: '{recorder._current_name}'\n\n"
                "I'm now watching browser activity. Navigate through the workflow "
                "you want to record, then tell me to stop recording."
            ),
            break_loop=False,
        )

    async def _stop_recording(self, recorder: Any, description: str) -> Response:
        try:
            playbook = await recorder.stop_recording(description=description)
        except RuntimeError as e:
            return Response(message=f"Cannot stop recording: {e}", break_loop=False)

        return Response(
            message=(
                f"Recording saved: '{playbook.name}'\n"
                f"  Domain: {playbook.domain}\n"
                f"  Steps: {len(playbook.steps)}\n"
                f"  Duration: {playbook.duration_ms / 1000:.1f}s\n"
                f"  Description: {playbook.description or '(none)'}\n\n"
                "Use bridge_replay to replay this playbook."
            ),
            break_loop=False,
        )

    def _list_playbooks(self, recorder: Any) -> Response:
        playbooks = recorder.list_playbooks()
        if not playbooks:
            return Response(
                message="No saved playbooks. Use bridge_record with action='start' to begin recording.",
                break_loop=False,
            )

        lines = ["Saved playbooks:\n"]
        for pb in playbooks:
            lines.append(
                f"  - {pb['name']} ({pb['domain']}) — "
                f"{pb['step_count']} steps, "
                f"{pb['duration_ms'] / 1000:.1f}s"
            )
            if pb.get("description"):
                lines.append(f"    {pb['description']}")

        return Response(message="\n".join(lines), break_loop=False)

    def _delete_playbook(self, recorder: Any, name: str) -> Response:
        if not name:
            return Response(
                message='A "name" argument is required to delete a playbook.',
                break_loop=False,
            )

        if recorder.delete_playbook(name):
            return Response(
                message=f"Playbook '{name}' deleted.",
                break_loop=False,
            )
        return Response(
            message=f"No playbook found with name '{name}'.",
            break_loop=False,
        )

    def _get_recorder(self) -> Any | None:
        """Get the PlaybookRecorder instance from the bridge plugin."""
        try:
            from plugins.browser_bridge.bridge import get_bridge
            bridge = get_bridge()
            if bridge and hasattr(bridge, "_playbook_recorder"):
                return bridge._playbook_recorder
        except ImportError:
            pass

        # Fallback: check if recorder is stored on the agent context
        try:
            ctx = self.agent.context
            if hasattr(ctx, "playbook_recorder"):
                return ctx.playbook_recorder
        except Exception:
            pass

        return None

    def get_log_object(self):
        action = self.args.get("action", "unknown")
        name = self.args.get("name", "")
        heading = f"icon://radio_button_checked {self.agent.agent_name}: Playbook Record"
        if action == "start" and name:
            heading += f" — start '{name}'"
        elif action == "stop":
            heading += " — stop"
        elif action == "list":
            heading += " — list"
        elif action == "delete" and name:
            heading += f" — delete '{name}'"

        return self.agent.context.log.log(
            type="tool",
            heading=heading,
            content="",
            kvps=self.args,
        )
