---
phase: 08-deduplication-and-filtering
plan: 02
subsystem: dedup
tags: [relevance-scoring, exclusion-patterns, filtering, pipeline-composition, high-recall]

# Dependency graph
requires:
  - phase: 08-01
    provides: deduplicate_by_url, deduplicate_by_title, _quality_score, normalize_url
  - phase: 03-heat-terms-dictionary
    provides: get_terms_by_category, TERM_CATEGORIES for scoring formula
  - phase: 02-data-models-and-geographic-data
    provides: Article model with frozen=True, relevance_score field, model_copy
provides:
  - score_relevance() scoring 0.0-1.0 based on term presence, category diversity, title bonus
  - filter_articles() with high-recall exclusion (score < 0.05 AND exclusion match only)
  - exclusion_patterns.json configurable without code changes
  - deduplicate_and_filter() composing URL dedup -> title dedup -> score -> filter
  - Package re-exports for all public dedup symbols
affects: [09-output, pipeline-integration, main-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Configurable data-driven exclusion via JSON (no code change needed)"
    - "Conjunctive exclusion patterns (cricket AND score, not cricket alone)"
    - "High-recall filter: exclude only if low score AND exclusion match"
    - "Pipeline composition function composing stages in order"
    - "lru_cache for single-read exclusion pattern loading"

key-files:
  created:
    - src/data/exclusion_patterns.json
    - src/dedup/_relevance.py
    - tests/test_relevance.py
  modified:
    - src/dedup/__init__.py

key-decisions:
  - "Conjunctive exclusion patterns (cricket AND score) to preserve heat articles mentioning sports venues"
  - "Score formula: (term_score * 0.5) + (category_score * 0.3) + title_bonus(0.2) capped at 1.0"
  - "full_text=None articles get 0.3 floor if title has heat terms (not penalized for extraction failure)"
  - "Exclude ONLY if score < 0.05 AND matches exclusion (high recall -- borderline kept)"
  - "English-only term matching in score_relevance (matches pipeline's English-first extraction)"

patterns-established:
  - "Data-driven configuration: exclusion_patterns.json editable without code changes"
  - "Pipeline composition: deduplicate_and_filter() as single entry point for downstream consumers"
  - "Frozen model update via model_copy(update={}) for relevance_score on frozen Pydantic models"

# Metrics
duration: 2min
completed: 2026-02-11
---

# Phase 8 Plan 02: Relevance Scoring and Pipeline Composition Summary

**Relevance scoring (term presence + category diversity + title bonus) with configurable exclusion patterns and deduplicate_and_filter() pipeline composing URL dedup, title dedup, scoring, and filtering**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-11T04:01:38Z
- **Completed:** 2026-02-11T04:04:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Relevance scoring formula using heat term presence (3+ terms = full term score), category diversity (2+ categories = full category score), and title bonus (+0.2)
- Configurable exclusion_patterns.json with 9 conjunctive patterns across sports, weather forecast, lifestyle, astrology, marketing, entertainment, and finance categories
- High-recall filtering: only excludes articles scoring below 0.05 AND matching an exclusion pattern
- deduplicate_and_filter() pipeline function composing all 3 stages as single public API entry point
- 10 new tests for relevance scoring and filtering, all passing alongside 20 existing dedup tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Exclusion patterns data file and relevance scoring**
   - `c085a23` (test: RED - failing tests for relevance scoring and filtering)
   - `b7baa14` (feat: GREEN - implement relevance scoring and exclusion-based filtering)

2. **Task 2: Pipeline composition and package re-exports**
   - `1c8c1b6` (feat: compose dedup+filter pipeline and package re-exports)

_TDD Task 1 had separate RED/GREEN commits._

## Files Created/Modified
- `src/data/exclusion_patterns.json` - 9 conjunctive exclusion patterns for irrelevant content
- `src/dedup/_relevance.py` - score_relevance(), filter_articles(), exclusion pattern loading
- `src/dedup/__init__.py` - deduplicate_and_filter() pipeline and all public re-exports
- `tests/test_relevance.py` - 10 tests for scoring and filtering

## Decisions Made
- Conjunctive exclusion patterns require multiple keywords (e.g., "cricket" AND "score/wicket/runs") to avoid removing legitimate heat articles that happen to mention sports venues
- Scoring formula weights: 50% term presence, 30% category diversity, 20% title bonus -- ensures articles with heat terms in the title rank higher
- Articles with full_text=None get a 0.3 score floor when title has heat terms -- extraction failure should not penalize an article's relevance
- Exclusion threshold set at 0.05 (not 0.0) combined with exclusion pattern match -- dual condition ensures high recall, only truly irrelevant articles are excluded
- English-only term matching in score_relevance using sorted TERM_CATEGORIES iteration for deterministic scoring

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete dedup+filter pipeline ready for downstream consumption via `from src.dedup import deduplicate_and_filter`
- Phase 8 fully complete: URL dedup, title dedup, relevance scoring, and filtering all operational
- 30 total tests across both test modules provide regression safety
- Next phases (Phase 9 output) can call deduplicate_and_filter(articles) as single pipeline entry point

## Self-Check: PASSED

All 5 files verified on disk (4 created + 1 modified). All 3 commit hashes verified in git log.

---
*Phase: 08-deduplication-and-filtering*
*Completed: 2026-02-11*
