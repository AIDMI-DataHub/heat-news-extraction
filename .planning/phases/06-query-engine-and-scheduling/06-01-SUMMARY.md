---
phase: 06-query-engine-and-scheduling
plan: 01
subsystem: query
tags: [dataclasses, query-generation, or-combining, character-limits, district-batching]

# Dependency graph
requires:
  - phase: 02-data-models-and-geographic-data
    provides: "StateUT, District models and geo_loader (36 states, 725 districts)"
  - phase: 03-heat-terms-dictionary
    provides: "564 heat terms across 14 languages, get_terms_by_category, TERM_CATEGORIES"
  - phase: 05-secondary-news-sources
    provides: "GNews supported languages list (8 langs), source character limits"
provides:
  - "Query and QueryResult frozen dataclasses for search query representation"
  - "QueryGenerator producing 800 Google, 100 NewsData, 87 GNews state-level queries"
  - "District-level query generation with batching within source character limits"
  - "build_category_query, build_broad_query, batch_districts helper functions"
  - "GNEWS_SUPPORTED_LANGUAGES constant (avoids circular imports)"
affects: [06-02, 06-03, query-scheduling, query-execution]

# Tech tracking
tech-stack:
  added: []
  patterns: [frozen-dataclasses-for-internal-objects, or-combined-query-strings, character-limit-aware-query-building]

key-files:
  created:
    - src/query/__init__.py
    - src/query/_models.py
    - src/query/_generator.py
  modified: []

key-decisions:
  - "Frozen dataclasses (not Pydantic) for Query/QueryResult -- internal objects with no I/O boundary validation needed"
  - "Sorted TERM_CATEGORIES iteration for deterministic query ordering across runs"
  - "First heatwave category term as primary heat term for district batching (most productive category)"
  - "GNEWS_SUPPORTED_LANGUAGES duplicated as constant to avoid circular imports from src.sources"

patterns-established:
  - "Query string format: (term1 OR \"multi word\" OR term3) LocationName"
  - "District batch format: heat_term (\"District1\" OR District2 OR \"District3\")"
  - "Character-limit-aware query building with priority-ordered term selection"

# Metrics
duration: 3min
completed: 2026-02-10
---

# Phase 6 Plan 1: Query Models and Generator Summary

**Frozen dataclass query models with OR-combined query generation producing 800 Google, 100 NewsData, and 87 GNews state-level queries from 564 heat terms across 36 states**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-10T12:03:49Z
- **Completed:** 2026-02-10T12:06:32Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Query and QueryResult frozen dataclasses with full type hints and source_hint field
- QueryGenerator.generate_state_queries produces exactly 800 Google (8 categories x 100 pairs), 100 NewsData, 87 GNews queries
- QueryGenerator.generate_district_queries batches UP's 75 districts into 3 queries within 2000 char limit
- build_category_query, build_broad_query, and batch_districts handle multi-word quoting and character limits correctly
- All query strings verified: parenthesized OR groups, location appended, no query exceeds source character limit

## Task Commits

Each task was committed atomically:

1. **Task 1: Create query data models and query string builders** - `0b0eaa2` (feat)
2. **Task 2: Create QueryGenerator class for state and district queries** - `3d693a0` (feat)

## Files Created/Modified
- `src/query/__init__.py` - Package re-exports for Query, QueryResult, QueryGenerator, helpers, GNEWS_SUPPORTED_LANGUAGES
- `src/query/_models.py` - Query/QueryResult frozen dataclasses + build_category_query, build_broad_query, batch_districts
- `src/query/_generator.py` - QueryGenerator with generate_state_queries and generate_district_queries methods

## Decisions Made
- **Frozen dataclasses over Pydantic:** Query/QueryResult are internal objects produced and consumed within the pipeline. No I/O boundary validation needed, so dataclasses avoid Pydantic overhead for potentially thousands of objects.
- **Sorted TERM_CATEGORIES:** Iterating categories in sorted order ensures deterministic query generation across runs, aiding debugging and reproducibility.
- **First heatwave term for district batching:** The "heatwave" category typically contains the most productive search terms. Using the first (highest-priority) term maximizes district query relevance.
- **GNEWS_SUPPORTED_LANGUAGES constant:** Duplicated from GNewsSource._SUPPORTED_LANGUAGES to prevent circular imports between src.query and src.sources packages.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Query models and generator ready for 06-02 (rate-limited scheduler) and 06-03 (query executor)
- QueryGenerator.generate_state_queries returns dict keyed by source_hint, ready for per-source scheduling
- QueryGenerator.generate_district_queries accepts source_hint parameter for source-specific char limits
- All query objects carry source_hint, language, state_slug, and level metadata needed by scheduler

## Self-Check: PASSED

- FOUND: src/query/__init__.py
- FOUND: src/query/_models.py
- FOUND: src/query/_generator.py
- FOUND: 06-01-SUMMARY.md
- FOUND: commit 0b0eaa2
- FOUND: commit 3d693a0

---
*Phase: 06-query-engine-and-scheduling*
*Completed: 2026-02-10*
