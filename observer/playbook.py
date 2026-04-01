"""
Playbook data model — recorded navigation sequences.

A Playbook is a list of PlaybookSteps captured from CDP events during a
recording session.  It can serialize to/from JSON and generate a standalone
Playwright Python script for replay.
"""

from __future__ import annotations

import json
import re
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PlaybookStep:
    """A single recorded action."""

    action: str
    timestamp: str
    url: str | None = None
    selector: str | None = None
    value: str | None = None
    text: str | None = None
    wait_ms: int | None = None
    method: str | None = None
    content_type: str | None = None
    # Robust locator strategies (captured during recording)
    tag: str | None = None
    role: str | None = None
    aria_label: str | None = None
    placeholder: str | None = None
    label_text: str | None = None
    input_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlaybookStep:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Playbook:
    """A recorded navigation sequence."""

    name: str
    domain: str
    description: str
    recorded_at: str
    steps: list[PlaybookStep] = field(default_factory=list)
    duration_ms: int = 0  # total recording time

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "recorded_at": self.recorded_at,
            "duration_ms": self.duration_ms,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Playbook:
        steps = [PlaybookStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            domain=data.get("domain", ""),
            description=data.get("description", ""),
            recorded_at=data.get("recorded_at", ""),
            duration_ms=data.get("duration_ms", 0),
            steps=steps,
        )

    def to_playwright_script(self, profile_dir: str = "data/profile") -> str:
        """Generate a standalone Playwright Python script that replays this playbook.

        Uses the bridge's persistent profile directory for auth so the replay
        inherits the same cookies/sessions as the recorded session.
        """
        nav_steps: list[str] = []
        for i, step in enumerate(self.steps):
            wait = min(step.wait_ms, 5000) if step.wait_ms else 500
            step_comment = f"# Step {i + 1}: {step.action}"
            if step.url:
                step_comment += f" — {step.url}"

            if step.action == "navigate" and step.url:
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    await page.goto({step.url!r})\n"
                    f"    await page.wait_for_load_state('networkidle')\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "click" and step.selector:
                label = f"  # {step.text}" if step.text else ""
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    await page.click({step.selector!r}){label}\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "type" and step.selector:
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    await page.fill({step.selector!r}, {step.value!r})\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "select" and step.selector:
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    await page.select_option({step.selector!r}, {step.value!r})\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "submit" and step.selector:
                label = f"  # submit: {step.text}" if step.text else ""
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    await page.click({step.selector!r}){label}\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "download" and step.value:
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    # Download detected: {step.value}\n"
                    f"    # (original URL: {step.url or 'unknown'})\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            elif step.action == "request" and step.url:
                nav_steps.append(
                    f"    {step_comment}\n"
                    f"    # {step.method or 'POST'} {step.url}\n"
                    f"    await asyncio.sleep({wait / 1000:.1f})"
                )
            else:
                nav_steps.append(
                    f"    {step_comment}\n    await asyncio.sleep({wait / 1000:.1f})"
                )

        steps_block = "\n\n".join(nav_steps) if nav_steps else "    pass"

        script = textwrap.dedent(f"""\
            #!/usr/bin/env python3
            \"\"\"
            Playwright replay script — {self.name}
            Domain: {self.domain}
            Recorded: {self.recorded_at}
            Steps: {len(self.steps)}

            Generated by Phantom Bridge playbook recorder.
            Uses persistent browser profile for authenticated sessions.
            \"\"\"

            import asyncio
            from pathlib import Path
            from playwright.async_api import async_playwright


            PROFILE_DIR = str(Path(__file__).resolve().parent / {profile_dir!r})


            async def main():
                async with async_playwright() as pw:
                    context = await pw.chromium.launch_persistent_context(
                        PROFILE_DIR,
                        headless=False,
                        viewport={{"width": 1280, "height": 900}},
                    )
                    page = context.pages[0] if context.pages else await context.new_page()

            {steps_block}

                    print("Playbook replay complete: {self.name}")
                    await context.close()


            if __name__ == "__main__":
                asyncio.run(main())
        """)
        return script

    def to_agent_instructions(self) -> str:
        """Generate natural-language workflow instructions for A0.

        Instead of a rigid Playwright script, produces human-readable steps
        with multi-strategy locator hints. A0 uses its reasoning to find
        elements when exact selectors fail.
        """
        action_verbs = {
            "navigate": "Navigate to {url}",
            "click": "Click {locator}",
            "type": "Type {value!r} into {locator}",
            "select": "Select {value!r} in {locator}",
            "submit": "Submit via {locator}",
            "download": "Wait for download: {value}",
            "request": "Note: {method} request to {url}",
        }

        def _locator(step: PlaybookStep) -> str:
            """Build a prioritized locator hint string."""
            hints = []
            if step.text:
                hints.append(f'text "{step.text}"')
            if step.aria_label:
                hints.append(f'aria-label "{step.aria_label}"')
            if step.label_text:
                hints.append(f'label "{step.label_text}"')
            if step.placeholder:
                hints.append(f'placeholder "{step.placeholder}"')
            if step.role:
                hints.append(f"role={step.role}")
            if step.selector:
                hints.append(f"selector: {step.selector}")
            return (
                "; try in order: " + ", ".join(hints) if hints else "(no locator hint)"
            )

        lines = [
            f"I recorded this workflow: {self.name}",
            f"Domain: {self.domain}",
            f"Steps: {len(self.steps)}",
            "",
            "Execute these steps in order. Use the locator hints to find elements.",
            "If a selector fails, fall back to the next hint (text > aria-label > role).",
            "",
        ]

        for i, step in enumerate(self.steps, 1):
            verb_template = action_verbs.get(step.action, "{action}")
            verb = verb_template.format(
                url=step.url or "",
                locator=_locator(step),
                value=step.value or "",
                method=step.method or "",
                action=step.action,
            )
            lines.append(f"{i}. {verb}")

        return "\n".join(lines)


def slugify(name: str) -> str:
    """Convert a name to a safe slug (lowercase, underscores, no spaces)."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")
