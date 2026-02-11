---
phase: 09-output-and-reliability
plan: 02
subsystem: reliability
tags: [circuit-breaker, tenacity, retry, checkpoint, aiofiles, rate-limiting]

# Dependency graph
requires:
  - phase: 06-query-engine-and-scheduling
    provides: SourceScheduler with budget/rate-limiting, Query/QueryResult models
  - phase: 04-google-news-rss-source
    provides: GoogleNewsSource with "never raises" pattern
  - phase: 05-secondary-news-sources
    provides: NewsDataSource, GNewsSource with "never raises" pattern
provides:
  - CircuitBreaker with closed/open/half_open state machine for per-source failure isolation
  - RateLimitError exception for HTTP 429 propagation from sources
  - with_rate_limit_retry tenacity decorator factory with exponential backoff + jitter
  - CheckpointStore with SHA-256 query keys and async JSON persistence via aiofiles
  - SourceScheduler circuit breaker integration (fail fast before budget check)
  - Tenacity retry wrapper around source calls in scheduler
affects: [09-output-and-reliability, query-executor, main-orchestration]

# Tech tracking
tech-stack:
  added: [tenacity wait_exponential_jitter, aiofiles for checkpoint I/O]
  patterns: [circuit breaker state machine, RateLimitError exception propagation, tenacity decorator factory, TYPE_CHECKING import guard for circular imports]

key-files:
  created:
    - src/reliability/__init__.py
    - src/reliability/_circuit_breaker.py
    - src/reliability/_retry.py
    - src/reliability/_checkpoint.py
  modified:
    - src/sources/google_news.py
    - src/sources/newsdata.py
    - src/sources/gnews.py
    - src/query/_scheduler.py

key-decisions:
  - "RateLimitError re-raised from sources ONLY for HTTP 429 -- preserves 'never raises' contract for all other errors"
  - "Circuit breaker check before budget check in scheduler (fail fast, don't wait for rate limiter)"
  - "success=True with error='circuit_breaker_open' for circuit breaker skip (same pattern as budget_exhausted)"
  - "Tenacity decorator defined as local function inside execute() to wrap source call cleanly"
  - "Inline import of RateLimitError in source except blocks to avoid circular imports"

patterns-established:
  - "Pattern: RateLimitError exception propagation -- sources re-raise HTTP 429 for tenacity, all other errors return []"
  - "Pattern: Circuit breaker as first check in scheduler execute() -- fail fast before any waiting"
  - "Pattern: Local async function with @with_rate_limit_retry() inside execute() for clean tenacity integration"
  - "Pattern: CheckpointStore uses SHA-256 truncated to 16 hex chars for stable query keys"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 9 Plan 2: Reliability Primitives Summary

**Circuit breaker (closed/open/half_open), tenacity retry with exponential backoff + jitter for HTTP 429, and checkpoint store with SHA-256 keys and aiofiles persistence -- integrated into SourceScheduler and all three source adapters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-11T05:01:30Z
- **Completed:** 2026-02-11T05:05:05Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created src/reliability/ package with CircuitBreaker, RateLimitError, with_rate_limit_retry, and CheckpointStore
- All three sources (google_news, newsdata, gnews) re-raise RateLimitError for HTTP 429 instead of silently returning []
- SourceScheduler.execute() checks circuit breaker first (fail fast), wraps source calls with tenacity retry, and records success/failure
- Factory functions accept optional circuit_breaker parameter for per-source isolation

## Task Commits

Each task was committed atomically:

1. **Task 1: Reliability primitives** - `47d2b5a` (feat)
2. **Task 2: Wire circuit breaker and retry into scheduler/sources** - `30329f8` (feat)

## Files Created/Modified
- `src/reliability/__init__.py` - Re-exports CircuitBreaker, RateLimitError, with_rate_limit_retry, CheckpointStore
- `src/reliability/_circuit_breaker.py` - Three-state circuit breaker with configurable threshold and timeout
- `src/reliability/_retry.py` - RateLimitError exception and tenacity decorator factory
- `src/reliability/_checkpoint.py` - CheckpointStore with SHA-256 query keys and aiofiles JSON persistence
- `src/sources/google_news.py` - Re-raises RateLimitError for HTTP 429
- `src/sources/newsdata.py` - Re-raises RateLimitError for HTTP 429
- `src/sources/gnews.py` - Re-raises RateLimitError for HTTP 429
- `src/query/_scheduler.py` - Circuit breaker check, tenacity retry wrapper, success/failure recording, factory updates

## Decisions Made
- RateLimitError re-raised from sources ONLY for HTTP 429 -- preserves "never raises" contract for all other errors
- Circuit breaker check is step 0 (before budget check) in scheduler -- fail fast, don't wait for rate limiter acquire
- success=True with error="circuit_breaker_open" for circuit breaker skip (same pattern as budget_exhausted -- expected skip, not failure)
- Tenacity decorator defined as a local function inside execute() to wrap the source.search() call cleanly without modifying the function signature
- Inline import of RateLimitError in source except blocks (only fires on rare 429 path, avoids circular imports)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Reliability primitives ready for integration with QueryExecutor (checkpoint tracking per query)
- Circuit breakers can be instantiated per-source in main.py orchestration
- Output writers (Plan 09-01) and final orchestration (Plan 09-03) can proceed

## Self-Check: PASSED

All 8 files verified present on disk. Both task commits (47d2b5a, 30329f8) verified in git log.

---
*Phase: 09-output-and-reliability*
*Completed: 2026-02-11*
