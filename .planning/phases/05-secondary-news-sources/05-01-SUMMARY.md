---
phase: 05-secondary-news-sources
plan: 01
subsystem: api
tags: [newsdata, httpx, rest-api, async, json, news-source]

# Dependency graph
requires:
  - phase: 04-google-news-rss-source
    provides: "NewsSource Protocol and GoogleNewsSource pattern to mirror"
  - phase: 02-data-models-and-geographic-data
    provides: "ArticleRef model for constructing search results"
provides:
  - "NewsDataSource class implementing NewsSource Protocol for newsdata.io API"
  - "Package-level re-export of NewsDataSource from src.sources"
affects: [05-02-gnews-source, 06-query-engine, 09-scheduling]

# Tech tracking
tech-stack:
  added: []
  patterns: [json-rest-api-adapter, daily-quota-tracking, graceful-no-key-degradation]

key-files:
  created:
    - src/sources/newsdata.py
  modified:
    - src/sources/__init__.py

key-decisions:
  - "All 14 Indian language codes in _SUPPORTED_LANGUAGES set (high recall principle)"
  - "In-memory daily quota counter (200/day) -- no persistence needed for daily batch pipeline"
  - "No follow_redirects on httpx client (not needed for REST API, unlike Google News RSS)"
  - "Increment _daily_count after request but before parsing (count the HTTP call, not the result)"
  - "Handle NewsData.io HTTP 200 error responses (status=error) alongside standard HTTP errors"

patterns-established:
  - "JSON REST API adapter pattern: mirror GoogleNewsSource structure with JSON parsing instead of RSS"
  - "Daily quota tracking: simple _daily_count integer, checked before each request"

# Metrics
duration: 2min
completed: 2026-02-10
---

# Phase 5 Plan 1: NewsData.io Source Adapter Summary

**NewsDataSource adapter for NewsData.io REST API with daily quota tracking, 14-language support, and graceful no-key degradation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-10T10:26:57Z
- **Completed:** 2026-02-10T10:28:29Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- NewsDataSource class implementing NewsSource Protocol for newsdata.io `/api/1/latest` endpoint
- Daily quota tracking (200 requests/day) with automatic cutoff when limit reached
- Graceful degradation when API key missing (returns [] without HTTP request)
- Full error handling: 401, 403 (sets quota to limit), 429, timeouts, network errors, JSON parse failures, and HTTP-200-with-error-status responses
- Package-level re-export from `src.sources`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create NewsDataSource adapter** - `74f28e8` (feat)
2. **Task 2: Update package re-exports** - `663a000` (feat)

## Files Created/Modified
- `src/sources/newsdata.py` - NewsDataSource class with _newsdata_to_ref() helper, full Protocol compliance
- `src/sources/__init__.py` - Added NewsDataSource import and __all__ entry

## Decisions Made
- All 14 Indian language codes included in `_SUPPORTED_LANGUAGES` set -- follows high recall principle; API returns empty results for unsupported languages rather than erroring
- `_daily_count` incremented after HTTP request but before response parsing -- counts the API credit consumed, not the parsing success
- Handles NewsData.io's HTTP 200 error pattern (`{"status": "error", ...}`) in addition to standard HTTP status codes
- No `follow_redirects=True` on httpx client -- REST API does not redirect like Google News RSS does

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

**External services require manual configuration.** The NEWSDATA_API_KEY environment variable must be set:
- Sign up at https://newsdata.io/register
- Navigate to Dashboard -> API Key
- Set `NEWSDATA_API_KEY` environment variable with the key value
- Without the key, NewsDataSource gracefully returns empty results

## Next Phase Readiness
- NewsDataSource ready for use by Phase 6 query engine
- Plan 05-02 (GNewsSource) can proceed independently -- same pattern, different API
- No blockers

## Self-Check: PASSED

- [x] src/sources/newsdata.py exists
- [x] src/sources/__init__.py exists (modified)
- [x] Commit 74f28e8 found in git log
- [x] Commit 663a000 found in git log
- [x] All 4 verification commands pass

---
*Phase: 05-secondary-news-sources*
*Completed: 2026-02-10*
