---
phase: 08-deduplication-and-filtering
plan: 01
subsystem: dedup
tags: [urllib, difflib, sequencematcher, url-normalization, deduplication]

# Dependency graph
requires:
  - phase: 02-data-models-and-geographic-data
    provides: Article model with frozen=True, full_text, district, source fields
provides:
  - normalize_url() for URL dedup comparison
  - deduplicate_by_url() removes URL duplicates keeping higher-quality version
  - deduplicate_by_title() removes title duplicates within same-language buckets
  - _quality_score() ranks articles by full_text length and metadata completeness
affects: [08-02-PLAN, 09-output, pipeline-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Functional pipeline stage: list[Article] -> list[Article]"
    - "URL normalization with stdlib urllib.parse (strip tracking, www, fragment, sort params)"
    - "Title similarity with difflib.SequenceMatcher and source suffix stripping"
    - "Language bucketing for O(k*(N/k)^2) title comparison"
    - "_quality_score shared between URL and title dedup modules"

key-files:
  created:
    - src/dedup/__init__.py
    - src/dedup/_url_dedup.py
    - src/dedup/_title_dedup.py
    - tests/test_dedup.py
  modified: []

key-decisions:
  - "Sorted list of tuples for urlencode to guarantee deterministic query param ordering"
  - "_quality_score() defined in _url_dedup.py and imported by _title_dedup.py to avoid duplication"
  - "Language bucketing prevents cross-language title comparison (Hindi vs English are different articles)"
  - "0.85 SequenceMatcher threshold after stripping source suffixes for title dedup"
  - "20 tracking parameters in _TRACKING_PARAMS frozenset for URL normalization"

patterns-established:
  - "Functional dedup stage: list[Article] -> list[Article] with no mutation"
  - "Quality scoring for duplicate resolution: full_text length > district > source"
  - "TDD with RED-GREEN commits for each dedup module"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 8 Plan 01: URL and Title Deduplication Summary

**URL normalization (tracking param stripping, www/fragment removal, param sorting) and title similarity dedup (SequenceMatcher with source suffix stripping, language bucketing) using stdlib only**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-11T03:55:39Z
- **Completed:** 2026-02-11T03:58:50Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- URL normalization that strips 20 tracking parameters, www prefix, fragments, trailing slashes, lowercases scheme/host, and sorts query params
- URL-based deduplication keeping the higher-quality version via _quality_score()
- Title-based deduplication with language bucketing, source suffix stripping, and 0.85 SequenceMatcher threshold
- 20 comprehensive tests covering normalization edge cases, dedup behavior, language isolation, and quality scoring

## Task Commits

Each task was committed atomically:

1. **Task 1: URL deduplication with tracking parameter normalization**
   - `1ef26ae` (test: RED - failing tests for URL normalization and deduplication)
   - `8c4e6b1` (feat: GREEN - implement URL normalization and URL-based deduplication)

2. **Task 2: Title similarity deduplication with language bucketing**
   - `7b2bfe1` (test: RED - failing tests for title dedup with language bucketing)
   - `bde6635` (feat: GREEN - implement title similarity dedup with language bucketing)

_TDD tasks had separate RED/GREEN commits._

## Files Created/Modified
- `src/dedup/__init__.py` - Empty placeholder (Plan 02 will populate re-exports)
- `src/dedup/_url_dedup.py` - normalize_url(), _quality_score(), deduplicate_by_url()
- `src/dedup/_title_dedup.py` - _strip_source_suffix(), _title_similarity(), deduplicate_by_title()
- `tests/__init__.py` - Tests package init
- `tests/test_dedup.py` - 20 tests for URL normalization, URL dedup, source suffix stripping, and title dedup

## Decisions Made
- Used sorted list of tuples (not dict) for urlencode to guarantee deterministic query parameter ordering -- dict iteration order depends on insertion order, not alphabetical
- Defined _quality_score() in _url_dedup.py and imported it in _title_dedup.py to avoid code duplication
- Language bucketing prevents cross-language title comparison -- Hindi and English versions of the same story are different articles worth keeping
- 0.85 SequenceMatcher threshold after stripping source suffixes catches "Headline - TOI" vs "Headline - NDTV" duplicates
- Source suffix stripping uses rfind(" - ") with 40-char length check to avoid stripping title content

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed non-deterministic query parameter sorting in normalize_url**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Using a dict comprehension for clean params then passing to urlencode produced non-deterministic ordering because dict preserves insertion order, not sorted order
- **Fix:** Changed to sorted list of tuples `sorted((k, sorted(v)) for k, v in params.items() ...)` before passing to urlencode
- **Files modified:** src/dedup/_url_dedup.py
- **Verification:** test_sorts_remaining_params now passes
- **Committed in:** 8c4e6b1 (part of Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Minor implementation fix for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- URL and title dedup modules ready for integration into dedup pipeline
- Plan 02 will add relevance scoring, filtering, and the dedup/__init__.py re-exports
- _quality_score() is reusable by both dedup stages

## Self-Check: PASSED

All 5 created files verified on disk. All 4 commit hashes verified in git log.

---
*Phase: 08-deduplication-and-filtering*
*Completed: 2026-02-11*
