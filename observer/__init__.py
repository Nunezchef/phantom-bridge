"""
Observer package — CDP-based browser observation layers.

Level 1: Auth Registry (Stream A)
Level 2: Sitemap Learner (Stream B)
Level 3: Playbook Recorder (Stream C)
"""

from __future__ import annotations

from .cdp_client import CDPClient
from .auth_registry import AuthRegistry, AuthEntry
from .manager import ObserverManager

__all__ = ["CDPClient", "AuthRegistry", "AuthEntry", "ObserverManager"]
