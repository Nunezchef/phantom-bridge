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

from helpers.tool import Tool, Response

logger = logging.getLogger("phantom_bridge")


class BridgeReplay(Tool):
    async def execute(self, **kwargs: Any) -> Response:
        name = self.args.get("name", "")
        dry_run = str(self.args.get("dry_run", "false")).lower() in ("true", "1", "yes")
        skip_health = str(self.args.get("skip_health_check", "false")).lower() in (
            "true",
            "1",
            "yes",
        )

        if not name:
            return Response(
                message=(
                    'Missing "name". Correct call:\n'
                    '{"tool":"bridge_replay","name":"my_workflow_name"}\n\n'
                    "To list available playbooks:\n"
                    '{"tool":"bridge_record","action":"list"}'
                ),
                break_loop=False,
            )

        recorder = self._get_recorder()
        if recorder is None:
            return Response(
                message=(
                    "Playbook recorder is not available — the browser bridge must be "
                    "running first. Start it with:\n"
                    '{"tool":"browser_bridge_open"}'
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

        # Pre-replay session health check
        if not skip_health and not dry_run and playbook.domain:
            health = await self._check_session_health(playbook.domain)
            if health is not None and not health.get("healthy", True):
                return Response(
                    message=(
                        f"Session health check FAILED for '{playbook.domain}'.\n"
                        f"Reason: {health.get('reason', 'unknown')}\n\n"
                        "The user needs to re-authenticate via the browser bridge "
                        "(bridge_open) before this playbook can be replayed.\n\n"
                        "To skip this check, set skip_health_check=true."
                    ),
                    break_loop=False,
                )

        # Resolve profile directory
        profile_dir = self._get_profile_dir()

        if dry_run:
            validation = await self._validate_playbook(playbook, profile_dir)
            script = playbook.to_playwright_script(profile_dir=profile_dir)
            msg_parts = [
                f"Playwright script for '{playbook.name}' "
                f"({len(playbook.steps)} steps):\n\n"
                f"```python\n{script}\n```\n\n"
                "Review and execute this script to replay the workflow.",
            ]
            if validation["errors"]:
                msg_parts.insert(
                    0,
                    f"Validation warnings for '{playbook.name}':\n"
                    + "\n".join(f"  - {e}" for e in validation["errors"])
                    + "\n",
                )
            else:
                msg_parts.insert(0, f"Validation passed for '{playbook.name}'.\n")
            return Response(message="\n".join(msg_parts), break_loop=False)

        # Live replay via Playwright
        return await self._replay_live(playbook, profile_dir)

    async def _replay_live(self, playbook: Any, profile_dir: str) -> Response:
        """Execute the playbook using Playwright with robust locator fallbacks."""
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
                            await page.goto(
                                step.url, wait_until="networkidle", timeout=30000
                            )

                        elif step.action == "click":
                            label = f" ({step.text})" if step.text else ""
                            progress_lines.append(
                                f"Step {step_num}/{total}: Click{label}"
                            )
                            await self._robust_click(page, step)

                        elif step.action == "type":
                            progress_lines.append(
                                f"Step {step_num}/{total}: Type into field"
                            )
                            await self._robust_fill(page, step)

                        elif step.action == "select":
                            progress_lines.append(
                                f"Step {step_num}/{total}: Select option"
                            )
                            await self._robust_select(page, step)

                        elif step.action == "submit":
                            label = f" ({step.text})" if step.text else ""
                            progress_lines.append(
                                f"Step {step_num}/{total}: Submit{label}"
                            )
                            await self._robust_click(page, step)

                        elif step.action == "download":
                            progress_lines.append(
                                f"Step {step_num}/{total}: Download — {step.value or 'file'}"
                            )
                        elif step.action == "request":
                            progress_lines.append(
                                f"Step {step_num}/{total}: {step.method or 'POST'} {step.url}"
                            )
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

    async def _robust_click(self, page, step) -> None:
        """Click with multi-strategy locator fallback chain."""
        # 1. Exact selector (fast path)
        if step.selector:
            try:
                await page.click(step.selector, timeout=3000)
                return
            except Exception:
                pass

        # 2. By visible text
        if step.text:
            try:
                await page.get_by_text(step.text, exact=False).first.click(timeout=3000)
                return
            except Exception:
                pass

        # 3. By role + name
        if step.role and step.text:
            try:
                await page.get_by_role(
                    step.role, name=step.text, exact=False
                ).first.click(timeout=3000)
                return
            except Exception:
                pass

        # 4. By role + aria-label (covers icon-only buttons/links)
        if step.aria_label and step.role:
            try:
                await page.get_by_role(
                    step.role, name=step.aria_label, exact=False
                ).first.click(timeout=3000)
                return
            except Exception:
                pass

        # 4b. By aria-label alone (any role)
        if step.aria_label:
            try:
                await page.locator(f'[aria-label="{step.aria_label}"]').first.click(
                    timeout=3000
                )
                return
            except Exception:
                pass

        # 5. Final attempt: loose selector
        if step.selector:
            await page.click(step.selector, timeout=10000)

    async def _robust_fill(self, page, step) -> None:
        """Fill input with multi-strategy locator fallback chain."""
        value = step.value or ""

        # 1. Exact selector
        if step.selector:
            try:
                await page.fill(step.selector, value, timeout=3000)
                return
            except Exception:
                pass

        # 2. By placeholder
        if step.placeholder:
            try:
                await page.get_by_placeholder(step.placeholder, exact=False).first.fill(
                    value, timeout=3000
                )
                return
            except Exception:
                pass

        # 3. By label
        if step.label_text:
            try:
                await page.get_by_label(step.label_text, exact=False).first.fill(
                    value, timeout=3000
                )
                return
            except Exception:
                pass

        # 4. By role + aria-label (use recorded role or infer from input_type)
        if step.aria_label:
            _INPUT_TYPE_ROLES = {
                "number": "spinbutton",
                "search": "searchbox",
                "email": "textbox",
                "password": "textbox",
                "tel": "textbox",
                "url": "textbox",
                "text": "textbox",
            }
            role = step.role or _INPUT_TYPE_ROLES.get(step.input_type or "", "textbox")
            try:
                await page.get_by_role(
                    role, name=step.aria_label, exact=False
                ).first.fill(value, timeout=3000)
                return
            except Exception:
                pass

        # 5. Final attempt
        if step.selector:
            await page.fill(step.selector, value, timeout=10000)

    async def _robust_select(self, page, step) -> None:
        """Select option with multi-strategy locator fallback chain."""
        value = step.value or ""

        # 1. Exact selector
        if step.selector:
            try:
                await page.select_option(step.selector, value, timeout=3000)
                return
            except Exception:
                pass

        # 2. By label
        if step.label_text:
            try:
                await page.get_by_label(
                    step.label_text, exact=False
                ).first.select_option(value, timeout=3000)
                return
            except Exception:
                pass

        # 3. By aria-label
        if step.aria_label:
            try:
                await page.get_by_label(
                    step.aria_label, exact=False
                ).first.select_option(value, timeout=3000)
                return
            except Exception:
                pass

        # 4. Final attempt
        if step.selector:
            await page.select_option(step.selector, value, timeout=10000)

    async def _check_session_health(self, domain: str) -> dict | None:
        """Check session health for the playbook's domain before replay.

        Returns the health check result dict, or None if the check
        could not be performed (observer unavailable).
        """
        try:
            from usr.plugins.phantom_bridge.bridge import get_bridge

            bridge = get_bridge()
            if bridge and bridge.is_running():
                manager = getattr(bridge, "_observer_manager", None)
                if manager and manager.auth:
                    return await manager.auth.check_session_health(domain)
        except Exception as exc:
            logger.debug("bridge_replay: health check failed: %s", exc)

        return None

    def _get_recorder(self) -> Any | None:
        """Get the PlaybookRecorder instance."""
        try:
            from usr.plugins.phantom_bridge.bridge import get_bridge

            bridge = get_bridge()
            if bridge:
                om = getattr(bridge, "_observer_manager", None)
                if om:
                    recorder = getattr(om, "_playbook", None)
                    if recorder:
                        return recorder
        except ImportError:
            pass

        try:
            ctx = self.agent.context
            if hasattr(ctx, "playbook_recorder"):
                return ctx.playbook_recorder
        except Exception:
            pass

        return None

    async def _validate_playbook(self, playbook: Any, profile_dir: str) -> dict:
        """Validate a playbook before replay.

        Checks:
        1. First navigation target is reachable
        2. Key selectors from first 3 interaction steps exist on the page
        Returns {"errors": [str], "warnings": [str]}
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            warnings.append("Playwright not installed — skipping validation")
            return {"errors": errors, "warnings": warnings}

        nav_steps = [s for s in playbook.steps if s.action == "navigate" and s.url]
        if not nav_steps:
            warnings.append("No navigation step found — cannot validate target URL")
            return {"errors": errors, "warnings": warnings}

        first_url = nav_steps[0].url
        interaction_steps = [
            s
            for s in playbook.steps[:10]
            if s.action in ("click", "type", "select", "submit") and s.selector
        ]

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

                try:
                    await page.goto(first_url, wait_until="networkidle", timeout=30000)
                except Exception as exc:
                    errors.append(f"Navigation to {first_url} failed: {exc}")
                    await context.close()
                    return {"errors": errors, "warnings": warnings}

                for step in interaction_steps[:3]:
                    try:
                        loc = page.locator(step.selector)
                        count = await loc.count()
                        if count == 0:
                            fallbacks = []
                            if step.text:
                                fallbacks.append(f"text={step.text}")
                            if step.aria_role:
                                fallbacks.append(f"role={step.aria_role}")
                            if step.aria_label:
                                fallbacks.append(f"aria-label={step.aria_label}")
                            if step.placeholder:
                                fallbacks.append(f"placeholder={step.placeholder}")
                            warnings.append(
                                f"Selector '{step.selector}' not found "
                                f"(step: {step.action})"
                                + (
                                    f", fallbacks available: {', '.join(fallbacks)}"
                                    if fallbacks
                                    else ""
                                )
                            )
                    except Exception:
                        pass

                await context.close()
        except Exception as exc:
            warnings.append(f"Validation failed: {exc}")

        return {"errors": errors, "warnings": warnings}

    async def _validate_playbook(self, playbook: Any, profile_dir: str) -> dict:
        """Validate a playbook before replay.

        Checks:
        1. First navigation target is reachable
        2. Key selectors from first 3 interaction steps exist on the page
        Returns {"errors": [str], "warnings": [str]}
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            warnings.append("Playwright not installed — skipping validation")
            return {"errors": errors, "warnings": warnings}

        nav_steps = [s for s in playbook.steps if s.action == "navigate" and s.url]
        if not nav_steps:
            warnings.append("No navigation step found — cannot validate target URL")
            return {"errors": errors, "warnings": warnings}

        first_url = nav_steps[0].url
        interaction_steps = [
            s
            for s in playbook.steps[:10]
            if s.action in ("click", "type", "select", "submit") and s.selector
        ]

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

                try:
                    await page.goto(first_url, wait_until="networkidle", timeout=30000)
                except Exception as exc:
                    errors.append(f"Navigation to {first_url} failed: {exc}")
                    await context.close()
                    return {"errors": errors, "warnings": warnings}

                for step in interaction_steps[:3]:
                    try:
                        loc = page.locator(step.selector)
                        count = await loc.count()
                        if count == 0:
                            fallbacks = []
                            if step.text:
                                fallbacks.append(f"text={step.text}")
                            if step.aria_role:
                                fallbacks.append(f"role={step.aria_role}")
                            if step.aria_label:
                                fallbacks.append(f"aria-label={step.aria_label}")
                            if step.placeholder:
                                fallbacks.append(f"placeholder={step.placeholder}")
                            warnings.append(
                                f"Selector '{step.selector}' not found "
                                f"(step: {step.action})"
                                + (
                                    f", fallbacks available: {', '.join(fallbacks)}"
                                    if fallbacks
                                    else ""
                                )
                            )
                    except Exception:
                        pass

                await context.close()
        except Exception as exc:
            warnings.append(f"Validation failed: {exc}")

        return {"errors": errors, "warnings": warnings}

    def _get_profile_dir(self) -> str:
        """Resolve the bridge's profile directory."""
        try:
            from usr.plugins.phantom_bridge.bridge import get_bridge

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
