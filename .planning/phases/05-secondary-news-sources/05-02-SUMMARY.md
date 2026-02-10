---
phase: 05-secondary-news-sources
plan: 02
subsystem: api
tags: [gnews, httpx, rest-api, async, json, news-source, quota-tracking]

# Dependency graph
requires:
  - phase: 04-google-news-rss-source
    provides: "NewsSource Protocol and GoogleNewsSource pattern to mirror"
  - phase: 05-secondary-news-sources
    plan: 01
    provides: "NewsDataSource pattern (sister adapter) and updated __init__.py"
  - phase: 02-data-models-and-geographic-data
    provides: "ArticleRef model for constructing search results"
provides:
  - "GNewsSource class implementing NewsSource Protocol for gnews.io API"
  - "Package-level re-export of all four source symbols from src.sources"
affects: [06-query-engine, 09-scheduling]

# Tech tracking
tech-stack:
  added: []
  patterns: [gnews-rest-api-adapter, 8-language-filter, http-403-quota-detection]

key-files:
  created:
    - src/sources/gnews.py
  modified:
    - src/sources/__init__.py

key-decisions:
  - "Only 8 languages in _SUPPORTED_LANGUAGES (en, hi, bn, ta, te, mr, ml, pa) -- GNews does NOT support gu, kn, or, as, ur, ne"
  - "In-memory daily quota counter (100/day) -- no persistence needed for daily batch pipeline"
  - "HTTP 403 = quota exhausted (sets _daily_count = _daily_limit), not an auth error"
  - "No follow_redirects on httpx client (REST API does not redirect)"
  - "Increment _daily_count after request but before parsing (count the HTTP call, not the result)"

patterns-established:
  - "Language subset filtering: GNews adapter checks _SUPPORTED_LANGUAGES before making request"
  - "HTTP 403 as quota signal: different from standard 401/403 semantics, handled specifically"

# Metrics
duration: 2min
completed: 2026-02-10
---

# Phase 5 Plan 2: GNews Source Adapter Summary

**GNewsSource adapter for gnews.io REST API with daily quota tracking (100/day), 8-language subset filter, and HTTP 403 quota exhaustion detection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-10T10:30:53Z
- **Completed:** 2026-02-10T10:32:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GNewsSource class implementing NewsSource Protocol for gnews.io `/api/v4/search` endpoint
- Daily quota tracking (100 requests/day) with automatic cutoff when limit reached
- Graceful degradation when API key missing (returns [] without HTTP request)
- Language filtering: only 8 of 14 Indian languages supported (en, hi, bn, ta, te, mr, ml, pa)
- Full error handling: 401 (invalid key), 403 (quota exhausted -- sets count to limit), 429 (per-second rate limit), timeouts, network errors, JSON parse failures
- All four source symbols now exported from `src.sources` package

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GNewsSource adapter** - `df8f233` (feat)
2. **Task 2: Update package re-exports** - `35583bf` (feat)

## Files Created/Modified
- `src/sources/gnews.py` - GNewsSource class with _gnews_to_ref() helper, full Protocol compliance, 8-language filter
- `src/sources/__init__.py` - Added GNewsSource import and __all__ entry (now exports all 4 symbols)

## Decisions Made
- Only 8 languages in `_SUPPORTED_LANGUAGES` set -- GNews officially supports en, hi, bn, ta, te, mr, ml, pa but NOT gu, kn, or, as, ur, ne (verified from GNews docs listing 26 total languages)
- `_daily_count` incremented after HTTP request but before response parsing -- counts the API credit consumed, not the parsing success (same pattern as NewsDataSource)
- HTTP 403 specifically detected as quota exhaustion signal (GNews uses 403, not 429, for daily limit) -- sets `_daily_count = _daily_limit` to prevent further requests
- No `follow_redirects=True` on httpx client -- REST API does not redirect like Google News RSS does

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

**External services require manual configuration.** The GNEWS_API_KEY environment variable must be set:
- Sign up at https://gnews.io/register
- Navigate to Dashboard -> API Key
- Set `GNEWS_API_KEY` environment variable with the key value
- Without the key, GNewsSource gracefully returns empty results

## Next Phase Readiness
- All three news source adapters complete (GoogleNewsSource, NewsDataSource, GNewsSource)
- Phase 5 complete -- all sources ready for Phase 6 query engine
- No blockers

## Self-Check: PASSED

- [x] src/sources/gnews.py exists
- [x] src/sources/__init__.py exists (modified)
- [x] Commit df8f233 found in git log
- [x] Commit 35583bf found in git log
- [x] All 6 verification commands pass

---
*Phase: 05-secondary-news-sources*
*Completed: 2026-02-10*
