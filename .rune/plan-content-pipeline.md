# Feature: Automated Content Pipeline

## Overview
Fully automated content pipeline that generates articles from NotebookLM, formats them into thread-style posts (3-4 per article), and publishes to both Threads and X — all via browser automation with zero APIs. Scheduled to produce 10 articles/day distributed from 8:30 AM to 5:30 PM (~54 min apart).

## Phases
| # | Name | Status | Plan File | Summary |
|---|------|--------|-----------|---------|
| 1 | Browser Automator | ⬚ Pending | plan-content-pipeline-phase1.md | Playwright wrapper with persistent profile, selector engine, element interaction |
| 2 | Site Drivers | ⬚ Pending | plan-content-pipeline-phase2.md | NotebookLM content extraction, Threads poster, X/Twitter poster |
| 3 | Content Engine | ⬚ Pending | plan-content-pipeline-phase3.md | Formatter (raw → thread posts), prompt templates, post queue |
| 4 | Scheduler + Pipeline + Tools | ⬚ Pending | plan-content-pipeline-phase4.md | Orchestrator, cron scheduler, A0 tools, config, logging |

## Key Decisions
- **Playwright over raw CDP**: Replay system already uses Playwright with persistent profile — higher-level selectors, auto-wait, network idle detection. CDP stays for observation only.
- **Configurable selectors**: Site drivers load selectors from `pipeline/selectors/*.yaml` — platforms change their DOM frequently, selectors must be updatable without code changes.
- **Queue-based pipeline**: Articles queue → format → post. If a post fails (selector changed, session expired), it retries or skips without blocking the schedule.
- **Auth registry gate**: Before every posting session, verify sessions via existing `auth_registry.json`. If expired, pause pipeline and notify user to re-authenticate.

## Architecture
```
Scheduler (cron: 8:30-17:30, every ~54min)
    → Pipeline Orchestrator
        → NotebookLM Driver (generate article via browser)
        → Content Formatter (split into 3-4 thread posts)
        → Threads Driver (post thread via browser)
        → X/Twitter Driver (post thread via browser)
        → Log result to pipeline/data/runs/
```

## Dependencies
- Playwright installed in container (`playwright install chromium`)
- User authenticated to NotebookLM, Threads, X via bridge beforehand
- Existing: auth_registry, bridge singleton, persistent profile

## Risks
- **Selector fragility**: Threads/X/NotebookLM update DOM → selectors break. Mitigation: YAML selector configs, screenshot-on-failure for debugging.
- **Rate limiting**: Posting too fast triggers platform anti-bot. Mitigation: human-like delays (2-5s between actions), randomized intervals.
- **Session expiry mid-day**: Auth cookies expire during the 9-hour window. Mitigation: pre-check auth registry before each article, pause + alert on expiry.
- **NotebookLM output variability**: Generated content length/format varies. Mitigation: formatter handles variable input, truncates/pads to target post count.

Awaiting approval before writing phase files.
