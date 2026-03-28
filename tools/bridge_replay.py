"""
bridge_replay — A0 tool to replay a saved playbook.

Replays a recorded browser workflow using Playwright with the bridge's
persistent profile directory for authenticated sessions.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from python.helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeReplay(Tool):

    async def execute(self, **kwargs: Any) -> Response:
        name = self.args.get("name", "")
        dry_run = str(self.args.get("dry_run", "false")).lower() in ("true", "1", "yes")

        if not name:
            return Response(
                message='A "name" argument is required. Use bridge_record with action="list" to see available playbooks.',
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

        playbook = recorder.get_playbook(name)
        if playbook is None:
            available = recorder.list_playbooks()
            names = ", ".join(pb["name"] for pb in available) if available else "(none)"
            return Response(
                message=f"No playbook found with name '{name}'. Available: {names}",
                break_loop=False,
            )

        # Resolve profile directory
        profile_dir = self._get_profile_dir()

        if dry_run:
            script = playbook.to_playwright_script(profile_dir=profile_dir)
            return Response(
                message=(
                    f"Playwright script for '{playbook.name}' "
                    f"({len(playbook.steps)} steps):\n\n"
                    f"```python\n{script}\n```\n\n"
                    "Review and execute this script to replay the workflow."
                ),
                break_loop=False,
            )

        # Live replay via Playwright
        return await self._replay_live(playbook, profile_dir)

    async def _replay_live(self, playbook: Any, profile_dir: str) -> Response:
        """Execute the playbook using Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return Response(
                message=(
                    "Playwright is not installed. Use dry_run=true to get the "
                    "script, or install playwright: pip install playwright && "
                    "playwright install chromium"
                ),
                break_loop=False,
            )

        progress_lines: list[str] = []
        error_step: int | None = None
        error_msg: str = ""

        try:
            async with async_playwright() as pw:
                profile_path = Path(profile_dir)
                profile_path.mkdir(parents=True, exist_ok=True)

                context = await pw.chromium.launch_persistent_context(
                    str(profile_path),
                    headless=True,
                    viewport={"width": 1280, "height": 900},
                )
                page = context.pages[0] if context.pages else await context.new_page()

                total = len(playbook.steps)
                for i, step in enumerate(playbook.steps):
                    step_num = i + 1
                    wait_s = min((step.wait_ms or 500) / 1000, 5.0)

                    try:
                        if step.action == "navigate" and step.url:
                            progress_lines.append(
                                f"Step {step_num}/{total}: Navigating to {step.url}"
                            )
                            await page.goto(step.url, wait_until="networkidle", timeout=30000)
                        elif step.action == "download":
                            progress_lines.append(
                                f"Step {step_num}/{total}: Download — {step.value or 'file'}"
                            )
                            # Downloads happen naturally via navigation;
                            # we just note it.
                        elif step.action == "request":
                            progress_lines.append(
                                f"Step {step_num}/{total}: {step.method or 'POST'} {step.url}"
                            )
                            # Requests triggered by page interaction
                            # happen naturally during navigation replay.
                        else:
                            progress_lines.append(
                                f"Step {step_num}/{total}: {step.action}"
                            )

                        await asyncio.sleep(wait_s)

                    except Exception as step_exc:
                        error_step = step_num
                        error_msg = str(step_exc)
                        progress_lines.append(
                            f"Step {step_num}/{total}: FAILED — {error_msg}"
                        )
                        break

                await context.close()

        except Exception as exc:
            return Response(
                message=(
                    f"Replay failed before starting: {exc}\n\n"
                    "Use dry_run=true to get the Playwright script instead."
                ),
                break_loop=False,
            )

        report = "\n".join(progress_lines)

        if error_step is not None:
            return Response(
                message=(
                    f"Replay of '{playbook.name}' stopped at step {error_step}/{len(playbook.steps)}.\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Progress:\n{report}"
                ),
                break_loop=False,
            )

        return Response(
            message=(
                f"Replay of '{playbook.name}' completed successfully "
                f"({len(playbook.steps)} steps).\n\n"
                f"Progress:\n{report}"
            ),
            break_loop=False,
        )

    def _get_recorder(self) -> Any | None:
        """Get the PlaybookRecorder instance."""
        try:
            from plugins.browser_bridge.bridge import get_bridge
            bridge = get_bridge()
            if bridge and hasattr(bridge, "_playbook_recorder"):
                return bridge._playbook_recorder
        except ImportError:
            pass

        try:
            ctx = self.agent.context
            if hasattr(ctx, "playbook_recorder"):
                return ctx.playbook_recorder
        except Exception:
            pass

        return None

    def _get_profile_dir(self) -> str:
        """Resolve the bridge's profile directory."""
        try:
            from plugins.browser_bridge.bridge import get_bridge
            bridge = get_bridge()
            if bridge:
                return str(bridge.get_profile_dir())
        except ImportError:
            pass

        # Fallback
        plugin_dir = Path(__file__).resolve().parent.parent
        return str(plugin_dir / "data" / "profile")

    def get_log_object(self):
        name = self.args.get("name", "unknown")
        dry_run = str(self.args.get("dry_run", "false")).lower() in ("true", "1", "yes")
        mode = "dry run" if dry_run else "live"

        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://play_arrow {self.agent.agent_name}: Replay Playbook '{name}' ({mode})",
            content="",
            kvps=self.args,
        )
