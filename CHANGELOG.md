# Changelog

## [1.1.0] - 2026-03-30

### Added
- **Cookie encryption at rest** — Cookie values are now encrypted using Fernet symmetric encryption before being written to disk. The encryption key is auto-generated at `data/.cookie_key` on first use. Cookie names and metadata remain in plaintext for structure inspection. Closes #3.
- **Per-domain cookie storage** — Cookies are now stored as individual files per domain at `data/cookies/<domain>.json` instead of a single monolithic `data/cookies.json`. A0 only loads cookies for the domain it needs, reducing token costs.
- **`bridge_decrypt_cookies` tool** — New A0 tool for on-demand cookie decryption. Returns plaintext cookie values in memory (never writes them to disk). Provides a ready-to-use `Cookie:` header string for HTTP requests.
- **`cryptography` dependency** — Added `cryptography>=42.0,<45.0` to requirements.txt for Fernet encryption support.

### Changed
- `api/bridge.py` — Cookie export, read, and delete operations now use encrypted per-domain files via `cookie_crypt` module.
- System prompt extension now teaches A0 about encrypted cookie storage and the `bridge_decrypt_cookies` tool.
- Updated README with new cookie management documentation, security details, and tool reference.

## [1.0.0] - 2026-03-28

Initial release.

- Remote browser control via noVNC (Xvfb + x11vnc + websockify)
- Session inheritance via shared Chromium profile directory
- Three-tier CDP observer system (auth registry, sitemap learner, playbook recorder)
- A0 system prompt injection with live session state
- WebUI sidebar panel with status, cookies, sitemaps, and playbooks
- 8 A0 tools for bridge management, auth queries, and workflow replay
