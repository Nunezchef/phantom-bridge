"""Simple metrics collector for Phantom Bridge observability."""

from __future__ import annotations

import time
from typing import Any


class MetricsCollector:
    """Thread-safe counter-based metrics collector."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._started_at = time.monotonic()

    def inc(self, name: str, amount: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + amount

    def get(self, name: str) -> int:
        return self._counters.get(name, 0)

    def snapshot(self) -> dict[str, Any]:
        uptime = time.monotonic() - self._started_at
        result = dict(self._counters)
        result["uptime_seconds"] = round(uptime, 1)
        total = result.get("cdp_events_total", 0)
        errors = result.get("errors_total", 0)
        if total > 0:
            result["error_rate"] = round(errors / total, 4)
        replayed = result.get("playbooks_replayed", 0)
        replay_success = result.get("playbooks_replay_success", 0)
        if replayed > 0:
            result["replay_success_rate"] = round(replay_success / replayed, 4)
        return result

    def reset(self) -> None:
        self._counters.clear()
        self._started_at = time.monotonic()


# Module-level singleton
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
