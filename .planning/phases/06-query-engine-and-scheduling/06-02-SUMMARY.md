---
phase: 06-query-engine-and-scheduling
plan: 02
subsystem: query
tags: [rate-limiting, asyncio, semaphore, rolling-window, budget-tracking, scheduling]

# Dependency graph
requires:
  - phase: 06-query-engine-and-scheduling
    plan: 01
    provides: "Query and QueryResult frozen dataclasses, QueryGenerator"
  - phase: 04-google-news-rss-source
    provides: "GoogleNewsSource implementing NewsSource Protocol"
  - phase: 05-secondary-news-sources
    provides: "NewsDataSource and GNewsSource implementing NewsSource Protocol"
provides:
  - "PerSecondLimiter: asyncio lock-based per-request delay with jitter"
  - "WindowLimiter: rolling-window rate limiter (e.g. 30 req/15 min)"
  - "SourceScheduler: wraps any NewsSource with budget, rate limiting, language filtering"
  - "Factory functions: create_google_scheduler, create_newsdata_scheduler, create_gnews_scheduler"
  - "execute() contract: never raises, always returns QueryResult"
affects: [06-03, query-execution, pipeline-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns: [asyncio-semaphore-concurrency, monotonic-time-rate-limiting, never-raise-wrapper-pattern]

key-files:
  created:
    - src/query/_scheduler.py
  modified:
    - src/query/__init__.py

key-decisions:
  - "TYPE_CHECKING import for NewsSource to avoid circular import at runtime"
  - "success=True with error field for expected skip conditions (budget exhausted, unsupported language) vs success=False for actual failures"
  - "Daily count incremented after HTTP request but before result processing (counts API credit, not successful parse)"
  - "time.monotonic() for all timing (immune to wall-clock adjustments)"

patterns-established:
  - "Never-raise wrapper: SourceScheduler.execute() catches all exceptions and returns error QueryResult"
  - "Budget-exhausted check before acquiring rate limiter (no unnecessary waits for dead sources)"
  - "Semaphore-based concurrency control per source (Google=5, others=1)"

# Metrics
duration: 2min
completed: 2026-02-10
---

# Phase 6 Plan 2: Source Scheduler Summary

**Rate-limit-aware SourceScheduler wrapping NewsSource with per-second delays, rolling windows, daily budgets, and per-source factory functions for Google (5 concurrent, 1.5/s), NewsData (200/day, 30/15min window), and GNews (100/day, 1/s)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-10T12:08:56Z
- **Completed:** 2026-02-10T12:10:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- PerSecondLimiter enforces minimum inter-request intervals with configurable jitter to avoid thundering herd
- WindowLimiter tracks rolling-window request counts with automatic pruning and blocking when full
- SourceScheduler.execute() wraps any NewsSource: budget check, language filter, semaphore, rate limiters, try/except -- never raises
- Three factory functions with correct per-source configurations matching API documentation
- Budget-exhausted and unsupported-language queries return immediately without consuming rate limiter slots

## Task Commits

Each task was committed atomically:

1. **Task 1: Create rate limiters and SourceScheduler** - `09546dc` (feat)
2. **Task 2: Update query package exports** - `9305c98` (feat)

## Files Created/Modified
- `src/query/_scheduler.py` - PerSecondLimiter, WindowLimiter, SourceScheduler classes and factory functions
- `src/query/__init__.py` - Re-exports all 6 scheduler symbols (3 classes + 3 factories)

## Decisions Made
- **TYPE_CHECKING import for NewsSource:** Avoids importing the Protocol class (and its transitive dependencies) at runtime. The type hint is only needed by static analysis tools and IDEs.
- **success=True for expected skips:** Budget exhaustion and unsupported language are normal control flow, not errors. Using success=True with a descriptive error field lets the executor distinguish retryable failures (success=False) from expected skips.
- **Daily count after request, not after parse:** Matches the pattern established in 05-01 and 05-02 -- the API credit is consumed by the HTTP request regardless of whether parsing succeeds.
- **time.monotonic() everywhere:** Wall-clock time can be adjusted (NTP, DST), but monotonic time only moves forward, making rate limiting robust against system clock changes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SourceScheduler ready for 06-03 (QueryExecutor) to orchestrate concurrent multi-source query execution
- Factory functions provide ready-to-use schedulers -- QueryExecutor just needs to call create_*_scheduler with source instances
- execute() contract (never raises, returns QueryResult) enables simple asyncio.gather() orchestration without error handling boilerplate
- All scheduler symbols exported from src.query package for clean imports

## Self-Check: PASSED

- FOUND: src/query/_scheduler.py
- FOUND: src/query/__init__.py
- FOUND: 06-02-SUMMARY.md
- FOUND: commit 09546dc
- FOUND: commit 9305c98

---
*Phase: 06-query-engine-and-scheduling*
*Completed: 2026-02-10*
