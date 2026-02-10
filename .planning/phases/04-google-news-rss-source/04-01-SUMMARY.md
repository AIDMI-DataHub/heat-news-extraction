---
phase: 04-google-news-rss-source
plan: 01
subsystem: sources
tags: [google-news, rss, feedparser, httpx, async, protocol, typing]

# Dependency graph
requires:
  - phase: 02-data-models-and-geographic-data
    provides: ArticleRef Pydantic model with IST date normalization and 14-language constraint
provides:
  - NewsSource Protocol (common async search() interface for all source adapters)
  - GoogleNewsSource class (fetches + parses Google News RSS into ArticleRef objects)
  - Package-level re-exports from src.sources
affects: [05-additional-news-sources, 06-query-engine, 07-article-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: [typing.Protocol for source interface, httpx async fetch + feedparser sync parse, dependency injection via optional AsyncClient]

key-files:
  created:
    - src/sources/_protocol.py
    - src/sources/google_news.py
  modified:
    - src/sources/__init__.py

key-decisions:
  - "typing.Protocol (structural subtyping) over abc.ABC for source interface"
  - "ceid parameter uses base language code (IN:en not IN:en-IN) to avoid Google News 302 redirects"
  - "follow_redirects=True on httpx.AsyncClient for robustness against Google News URL normalization"
  - "Store Google News redirect URLs as-is in ArticleRef.url -- resolution deferred to Phase 7"
  - "Lazy httpx.AsyncClient creation with async context manager for clean lifecycle"

patterns-established:
  - "Source adapter pattern: class with async search() returning list[ArticleRef], never raises"
  - "Protocol satisfaction via structural subtyping (no inheritance)"
  - "Dependency injection: optional httpx.AsyncClient in constructor for shared connection pools"
  - "Module-level _entry_to_article_ref() helper for RSS entry conversion with graceful skip on bad entries"

# Metrics
duration: 3min
completed: 2026-02-10
---

# Phase 4 Plan 1: Google News RSS Source Summary

**NewsSource Protocol with async search() interface and GoogleNewsSource adapter parsing Google News RSS into ArticleRef objects via httpx + feedparser**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-10T10:00:40Z
- **Completed:** 2026-02-10T10:03:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- NewsSource Protocol defines the common `async search()` interface for all source adapters (Phase 5 sources will satisfy it too)
- GoogleNewsSource fetches Google News RSS via httpx and parses entries via feedparser into valid ArticleRef objects
- Live verification confirmed: 100 articles parsed for "heat wave India" query with correct fields (title, url, source, date in IST, language, state, search_term)
- All 14 Indian language codes mapped to Google News hl parameter (en -> en-IN for India-specific English)
- Error handling verified: HTTP errors, timeouts, and bad queries return empty list without raising

## Task Commits

Each task was committed atomically:

1. **Task 1: Create NewsSource Protocol and GoogleNewsSource implementation** - `988e047` (feat)
2. **Task 2: Update package re-exports and run live verification** - `f7205a1` (feat)

## Files Created/Modified
- `src/sources/_protocol.py` - NewsSource Protocol with runtime_checkable decorator and async search() method
- `src/sources/google_news.py` - GoogleNewsSource class with httpx fetch, feedparser parse, 14-language mapping, error handling
- `src/sources/__init__.py` - Re-exports NewsSource and GoogleNewsSource for clean package-level imports

## Decisions Made
- **typing.Protocol over abc.ABC**: Structural subtyping means Phase 5 sources satisfy the interface without inheritance
- **ceid uses base language code**: `ceid=IN:en` not `ceid=IN:en-IN` -- the latter causes Google News 302 redirects to the corrected URL
- **follow_redirects=True**: Google News may redirect URLs during normalization; following redirects makes the adapter more robust
- **No URL resolution at search time**: Google News redirect URLs stored as-is; actual article URL resolution belongs in Phase 7
- **Lazy client creation**: httpx.AsyncClient created on first search() call, not in constructor, allowing dependency injection for Phase 6

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ceid parameter format causing 302 redirects**
- **Found during:** Task 2 (live verification)
- **Issue:** URL used `ceid=IN:en-IN` but Google News expects `ceid=IN:en` (base language code, not hl variant). This caused 302 redirects which httpx treated as errors.
- **Fix:** Changed _build_url() to use `language` (base code) instead of `hl` (variant) for ceid. Also enabled `follow_redirects=True` on the httpx client for additional robustness.
- **Files modified:** src/sources/google_news.py
- **Verification:** Live search returned 100 articles after fix (was returning 0 before)
- **Committed in:** f7205a1 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- without it, all searches returned 0 results due to unhandled 302 redirect. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- NewsSource Protocol ready for Phase 5 sources (NewsData.io, GNews) to implement
- GoogleNewsSource.search() ready for Phase 6 query engine to call
- src.sources package cleanly exports both Protocol and implementation
- Blocker note: Google News RSS rate limiting from GitHub Actions IPs remains an open concern (Phase 9 will add circuit breaker)

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 04-google-news-rss-source*
*Completed: 2026-02-10*
