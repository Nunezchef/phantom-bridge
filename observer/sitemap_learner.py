"""
sitemap_learner — Records URLs visited via CDP, extracts patterns,
and builds per-domain feature maps.

Part of the Phantom Bridge observer layer.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .cdp_client import CDPClient

logger = logging.getLogger("phantom_bridge")


def _safe_str(s: str) -> str:
    """Strip lone Unicode surrogates that break JSON serialisation.

    Some web pages contain malformed UTF-16 sequences (lone surrogates U+D800–
    U+DFFF) in their titles or URLs.  Python's json.dumps raises UnicodeEncodeError
    on these, which silently swallows the whole sitemap save.  Round-tripping
    through UTF-8 with errors='replace' eliminates them.
    """
    return s.encode("utf-8", errors="replace").decode("utf-8")

# Extensions to ignore (static assets, fonts, etc.)
_SKIP_EXTENSIONS = frozenset({
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".map",
    ".json", ".xml",
})

# Schemes to accept
_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Regex patterns for dynamic URL segments
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_MONGO_OID_RE = re.compile(r"^[0-9a-f]{24}$", re.I)
_NUMERIC_ID_RE = re.compile(r"^\d{4,}$")
_SHORT_ALPHANUM_RE = re.compile(r"^[a-zA-Z0-9]{8,12}$")

# Words that look like short alphanum but are real path segments
_COMMON_WORDS = frozenset({
    "settings", "dashboard", "overview", "analytics", "calendar",
    "schedule", "messages", "comments", "activity", "feedback",
    "checkout", "payments", "products", "invoices", "accounts",
    "customers", "employee", "services", "delivery", "catering",
    "training", "onboard",
})

# Max raw URLs to keep per pattern (for debugging)
_MAX_RAW_URLS = 5
# Max unique titles to keep per pattern
_MAX_TITLES = 5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageVisit:
    pattern: str
    titles: list[str] = field(default_factory=list)
    visit_count: int = 0
    first_visited: str = ""
    last_visited: str = ""
    raw_urls: list[str] = field(default_factory=list)


@dataclass
class Feature:
    name: str
    pages: list[PageVisit] = field(default_factory=list)
    prefix: str = ""


@dataclass
class DomainSitemap:
    domain: str
    features: dict[str, Feature] = field(default_factory=dict)
    total_visits: int = 0
    first_seen: str = ""
    last_seen: str = ""
    # Flat index of all page visits keyed by parameterized pattern
    _pages: dict[str, PageVisit] = field(default_factory=dict, repr=False)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _sitemap_to_dict(sm: DomainSitemap) -> dict:
    """Serialize a DomainSitemap to a JSON-friendly dict."""
    features = {}
    for fname, feat in sm.features.items():
        features[fname] = {
            "name": feat.name,
            "prefix": feat.prefix,
            "pages": [asdict(p) for p in feat.pages],
        }
    return {
        "domain": sm.domain,
        "features": features,
        "total_visits": sm.total_visits,
        "first_seen": sm.first_seen,
        "last_seen": sm.last_seen,
    }


def _sitemap_from_dict(d: dict) -> DomainSitemap:
    """Deserialize a dict into a DomainSitemap."""
    sm = DomainSitemap(
        domain=d["domain"],
        total_visits=d.get("total_visits", 0),
        first_seen=d.get("first_seen", ""),
        last_seen=d.get("last_seen", ""),
    )
    for fname, fdata in d.get("features", {}).items():
        pages = [PageVisit(**p) for p in fdata.get("pages", [])]
        feat = Feature(name=fdata["name"], prefix=fdata.get("prefix", ""), pages=pages)
        sm.features[fname] = feat
        for pv in pages:
            sm._pages[pv.pattern] = pv
    return sm


# ---------------------------------------------------------------------------
# SitemapLearner
# ---------------------------------------------------------------------------

class SitemapLearner:
    """Records URLs visited, extracts patterns, builds per-domain feature maps."""

    def __init__(self, cdp: CDPClient, data_dir: Path) -> None:
        self._cdp = cdp
        self._data_dir = data_dir / "sitemaps"
        self._sitemaps: dict[str, DomainSitemap] = {}

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to Page navigation events and load persisted data."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()
        await self._cdp.subscribe("Page.frameNavigated", self._on_navigated)
        await self._cdp.subscribe("Page.navigatedWithinDocument", self._on_spa_nav)
        logger.info("SitemapLearner started — tracking %d domains", len(self._sitemaps))

    async def stop(self) -> None:
        """Persist all sitemaps to disk."""
        self._save_all()
        logger.info("SitemapLearner stopped — saved %d domains", len(self._sitemaps))

    # -- CDP event handlers --------------------------------------------------

    async def _on_navigated(self, params: dict) -> None:
        """Handle full page navigation (Page.frameNavigated)."""
        frame = params.get("frame", {})
        url = frame.get("url", "")
        if not self._should_record(url):
            return
        title = await self._fetch_title()
        self._record_visit(url, title)

    async def _on_spa_nav(self, params: dict) -> None:
        """Handle SPA in-document navigation (Page.navigatedWithinDocument)."""
        url = params.get("url", "")
        if not self._should_record(url):
            return
        title = await self._fetch_title()
        self._record_visit(url, title)

    # -- title extraction ----------------------------------------------------

    async def _fetch_title(self) -> str | None:
        """Use Runtime.evaluate to grab document.title from the page."""
        try:
            result = await self._cdp.send(
                "Runtime.evaluate",
                {"expression": "document.title", "returnByValue": True},
            )
            value = result.get("result", {}).get("value")
            if isinstance(value, str) and value.strip():
                return _safe_str(value.strip())
        except Exception:
            logger.debug("Failed to fetch document.title", exc_info=True)
        return None

    # -- URL filtering -------------------------------------------------------

    @staticmethod
    def _should_record(url: str) -> bool:
        """Return True if this URL is worth recording."""
        if not url:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            return False
        # Check file extension
        path_lower = parsed.path.lower()
        for ext in _SKIP_EXTENSIONS:
            if path_lower.endswith(ext):
                return False
        return True

    # -- recording -----------------------------------------------------------

    def _record_visit(self, url: str, title: str | None) -> None:
        """Record a URL visit into the appropriate domain sitemap."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return

        now = datetime.now(timezone.utc).isoformat()

        # Get or create sitemap for domain
        if domain not in self._sitemaps:
            self._sitemaps[domain] = DomainSitemap(
                domain=domain,
                first_seen=now,
                last_seen=now,
            )
        sm = self._sitemaps[domain]
        sm.last_seen = now
        sm.total_visits += 1

        # Parameterize the path
        pattern = self._parameterize_url(parsed.path or "/")

        # Get or create PageVisit
        if pattern not in sm._pages:
            pv = PageVisit(
                pattern=pattern,
                first_visited=now,
                last_visited=now,
            )
            sm._pages[pattern] = pv
        else:
            pv = sm._pages[pattern]

        pv.visit_count += 1
        pv.last_visited = now

        # Sanitize title before storing (lone surrogates break JSON serialization)
        if title:
            title = _safe_str(title)

        # Add title (deduplicated)
        if title and title not in pv.titles:
            if len(pv.titles) >= _MAX_TITLES:
                pv.titles.pop(0)
            pv.titles.append(title)

        # Track raw URLs (ring buffer)
        if url not in pv.raw_urls:
            if len(pv.raw_urls) >= _MAX_RAW_URLS:
                pv.raw_urls.pop(0)
            pv.raw_urls.append(url)

        # Re-group features after every new pattern
        self._auto_group_features(sm)

        # Periodic save (every 10 visits)
        if sm.total_visits % 10 == 0:
            self._save_domain(sm)

    # -- URL parameterization ------------------------------------------------

    @staticmethod
    def _parameterize_url(path: str) -> str:
        """Replace dynamic segments in URL path with {id} placeholders.

        Handles UUIDs, numeric IDs (4+ digits), MongoDB ObjectIds,
        and short alphanumeric tokens that don't look like real words.
        """
        segments = path.strip("/").split("/")
        result: list[str] = []
        for seg in segments:
            if not seg:
                continue
            if _UUID_RE.match(seg):
                result.append("{id}")
            elif _NUMERIC_ID_RE.match(seg):
                result.append("{id}")
            elif _MONGO_OID_RE.match(seg):
                result.append("{id}")
            elif _SHORT_ALPHANUM_RE.match(seg) and seg.lower() not in _COMMON_WORDS:
                # Only replace if it doesn't look like a normal word
                # Additional heuristic: if it has digits mixed in, it's likely an ID
                if any(c.isdigit() for c in seg):
                    result.append("{id}")
                else:
                    result.append(seg)
            else:
                result.append(seg)
        return "/" + "/".join(result) if result else "/"

    # -- feature auto-grouping -----------------------------------------------

    @staticmethod
    def _auto_group_features(sitemap: DomainSitemap) -> None:
        """Group URL patterns by common prefix into feature areas.

        Uses the first meaningful path segment (after any {id} segments)
        as the feature name. Falls back to "Root" for top-level pages.
        """
        # Collect all page visits
        all_pages = list(sitemap._pages.values())
        if not all_pages:
            return

        # Group by first meaningful segment
        groups: dict[str, list[PageVisit]] = {}
        prefixes: dict[str, str] = {}

        for pv in all_pages:
            segments = [s for s in pv.pattern.strip("/").split("/") if s]
            # Find first non-{id} segment
            feature_name = "Root"
            prefix = "/"
            for i, seg in enumerate(segments):
                if seg != "{id}":
                    feature_name = seg.replace("-", " ").replace("_", " ").title()
                    prefix = "/" + "/".join(segments[: i + 1])
                    break

            if feature_name not in groups:
                groups[feature_name] = []
                prefixes[feature_name] = prefix
            groups[feature_name].append(pv)

        # Rebuild features dict
        sitemap.features.clear()
        for fname, pages in sorted(groups.items()):
            sitemap.features[fname] = Feature(
                name=fname,
                pages=sorted(pages, key=lambda p: p.pattern),
                prefix=prefixes[fname],
            )

    # -- public query API ----------------------------------------------------

    def get_sitemap(self, domain: str) -> dict | None:
        """Return sitemap for a domain as a serializable dict."""
        sm = self._sitemaps.get(domain)
        if sm is None:
            return None
        return _sitemap_to_dict(sm)

    def get_all_domains(self) -> list[str]:
        """Return list of domains with recorded sitemaps."""
        return sorted(self._sitemaps.keys())

    # -- persistence ---------------------------------------------------------

    def _save_domain(self, sm: DomainSitemap) -> None:
        """Persist a single domain sitemap to JSON."""
        safe_name = sm.domain.replace(":", "_").replace("/", "_")
        path = self._data_dir / f"{safe_name}.json"
        try:
            path.write_text(json.dumps(_sitemap_to_dict(sm), indent=2))
        except Exception:
            logger.error("Failed to save sitemap for %s", sm.domain, exc_info=True)

    def _save_all(self) -> None:
        """Persist all domain sitemaps."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        for sm in self._sitemaps.values():
            self._save_domain(sm)

    def _load_all(self) -> None:
        """Load existing sitemaps from disk on startup."""
        if not self._data_dir.exists():
            return
        for path in self._data_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                sm = _sitemap_from_dict(data)
                self._sitemaps[sm.domain] = sm
                logger.debug("Loaded sitemap for %s (%d pages)", sm.domain, len(sm._pages))
            except Exception:
                logger.warning("Failed to load sitemap from %s", path, exc_info=True)
