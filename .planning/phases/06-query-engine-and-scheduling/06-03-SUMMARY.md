---
phase: 06-query-engine-and-scheduling
plan: 03
subsystem: query
tags: [asyncio-taskgroup, hierarchical-execution, state-then-district, concurrent-sources, query-orchestration]

# Dependency graph
requires:
  - phase: 06-query-engine-and-scheduling
    plan: 01
    provides: "Query/QueryResult dataclasses, QueryGenerator with state and district query generation"
  - phase: 06-query-engine-and-scheduling
    plan: 02
    provides: "SourceScheduler with rate limiting, budget tracking, and per-source factory functions"
  - phase: 02-data-models-and-geographic-data
    provides: "StateUT model and get_all_regions() for loading geographic data"
provides:
  - "QueryExecutor orchestrating hierarchical state-then-district execution"
  - "Concurrent multi-source execution via asyncio.TaskGroup"
  - "Budget-aware district query skipping for exhausted sources"
  - "Complete src.query package with 14 public symbols across 4 submodules"
affects: [pipeline-orchestration, daily-collection, main-entry-point]

# Tech tracking
tech-stack:
  added: []
  patterns: [asyncio-taskgroup-parallel-sources, hierarchical-query-execution, exception-group-handling]

key-files:
  created:
    - src/query/_executor.py
  modified:
    - src/query/__init__.py

key-decisions:
  - "asyncio.TaskGroup for concurrent source execution with except* ExceptionGroup for robustness"
  - "Sequential query execution within each source (scheduler handles internal rate limiting)"
  - "Budget check before district query generation (not just before execution)"
  - "Flat ArticleRef list return -- no nested structure, consumer just iterates"

patterns-established:
  - "Two-phase hierarchical execution: state queries first, district drill-down for active states only"
  - "ExceptionGroup handling via except* -- log all errors, never crash, return partial results"
  - "Budget-aware phase transitions: skip district queries for sources with exhausted budgets"

# Metrics
duration: 2min
completed: 2026-02-10
---

# Phase 6 Plan 3: Query Executor Summary

**QueryExecutor orchestrating hierarchical state-then-district execution across concurrent sources via asyncio.TaskGroup with budget-aware district drill-down**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-10T12:13:28Z
- **Completed:** 2026-02-10T12:15:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- QueryExecutor.run_collection() implements two-phase hierarchical execution: state-level queries first across all sources in parallel, then district-level queries only for states that returned articles
- All three sources execute concurrently via asyncio.TaskGroup (not sequentially); each source processes its queries sequentially through its SourceScheduler
- Budget-exhausted sources are automatically skipped for district queries, preventing wasted API calls
- Complete src.query package with 14 public symbols across 4 submodules (models, generator, scheduler, executor)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create QueryExecutor with hierarchical execution** - `6defac5` (feat)
2. **Task 2: Update query package exports and verify full integration** - `af3de9f` (feat)

## Files Created/Modified
- `src/query/_executor.py` - QueryExecutor class with run_collection, _execute_queries_parallel, and _execute_query_list methods
- `src/query/__init__.py` - Updated with QueryExecutor import/export and expanded module docstring describing all 4 submodules

## Decisions Made
- **asyncio.TaskGroup with except* ExceptionGroup:** Python 3.11+ TaskGroup provides structured concurrency. Using except* catches any ExceptionGroup from failed source tasks without losing partial results from successful sources.
- **Sequential queries within source, concurrent across sources:** Each SourceScheduler already handles rate limiting internally. Running queries sequentially within a source respects the scheduler's concurrency/rate controls, while running sources in parallel maximizes throughput.
- **Budget check before district generation:** Checking remaining_budget before calling generate_district_queries avoids generating queries that would immediately be skipped, saving computation.
- **Flat ArticleRef return:** Returning a flat list (not grouped by source or state) simplifies the consumer interface. State/source metadata is already embedded in each ArticleRef via its fields.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Query engine package fully complete: QueryGenerator produces queries, SourceScheduler wraps sources with rate limiting, QueryExecutor orchestrates hierarchical execution
- Pipeline orchestration (future phase) can call `QueryExecutor.run_collection()` with a single await to collect all articles
- Factory functions (create_google_scheduler, create_newsdata_scheduler, create_gnews_scheduler) provide ready-to-use schedulers
- Phase 6 is complete (all 3 plans executed)

## Self-Check: PASSED

- FOUND: src/query/_executor.py
- FOUND: src/query/__init__.py
- FOUND: 06-03-SUMMARY.md
- FOUND: commit 6defac5
- FOUND: commit af3de9f

---
*Phase: 06-query-engine-and-scheduling*
*Completed: 2026-02-10*
