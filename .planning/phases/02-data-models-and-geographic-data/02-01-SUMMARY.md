---
phase: 02-data-models-and-geographic-data
plan: 01
subsystem: models
tags: [pydantic, pydantic-v2, datetime, timezone, ist, zoneinfo, validation]

# Dependency graph
requires:
  - phase: 01-project-foundation
    provides: "Project structure with src/models/ package and pydantic==2.10.6 dependency"
provides:
  - "ArticleRef Pydantic v2 model for search result metadata"
  - "Article Pydantic v2 model with full_text and relevance_score"
  - "IST timezone constant and automatic date normalization"
  - "Clean re-exports from src.models package"
affects: [03-source-adapters, 04-google-news-rss, 05-newsdata-api, 06-search-query-engine, 07-article-extraction, 08-relevance-filtering, 09-output-and-storage, 10-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 frozen models with ConfigDict(frozen=True)"
    - "IST timezone normalization via field_validator + BeforeValidator"
    - "Two-stage model pattern: ArticleRef -> Article inheritance"
    - "Annotated type alias (ISTAwareDatetime) for reusable date validation"

key-files:
  created:
    - src/models/article.py
  modified:
    - src/models/__init__.py

key-decisions:
  - "Two-model pattern (ArticleRef -> Article) to support pipeline stages where full_text is added later via model_copy"
  - "BeforeValidator coerces naive datetimes to IST rather than rejecting them, preventing pipeline crashes from inconsistent news sources"
  - "Language field constrained to 14 codes via regex pattern, not enum, for Pydantic v2 compatibility"
  - "str type for url field instead of HttpUrl to handle unusual Google News URL schemes"

patterns-established:
  - "Frozen Pydantic models: all domain models use ConfigDict(frozen=True) for immutability"
  - "IST normalization: all dates pass through coerce_naive_to_ist + astimezone(IST)"
  - "Clean package re-exports: src/models/__init__.py re-exports key symbols"

# Metrics
duration: 2min
completed: 2026-02-10
---

# Phase 2 Plan 1: Article Models Summary

**ArticleRef and Article Pydantic v2 frozen models with IST timezone normalization via BeforeValidator and field_validator**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-10T09:00:11Z
- **Completed:** 2026-02-10T09:01:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ArticleRef model with 8 typed fields (title, url, source, date, language, state, district, search_term) and strict validation
- Article model extending ArticleRef with full_text and relevance_score (0.0-1.0 range)
- Automatic IST timezone normalization: UTC/any-timezone dates converted, naive datetimes assumed IST
- Language field constrained to 14 supported Indian language codes via regex pattern
- Both models frozen for immutability; clean re-exports from src.models package

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ArticleRef and Article Pydantic models with IST date validation** - `e26c911` (feat)
2. **Task 2: Update models __init__.py to re-export article models** - `8fd8f6a` (feat)

## Files Created/Modified
- `src/models/article.py` - ArticleRef and Article Pydantic v2 models with IST date validation, BeforeValidator for naive datetimes, frozen ConfigDict
- `src/models/__init__.py` - Re-exports Article, ArticleRef, IST for clean package-level imports

## Decisions Made
- Two-model pattern (ArticleRef -> Article) chosen to support the pipeline lifecycle: source adapters create ArticleRef, extraction enriches into Article via model_copy
- BeforeValidator coerces naive datetimes to IST rather than rejecting -- prevents pipeline crashes from news sources that omit timezone info
- Used str type for url field instead of Pydantic HttpUrl to accommodate unusual Google News URL schemes
- Language constraint via regex pattern rather than Literal/Enum for simpler Pydantic v2 field definition

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ArticleRef and Article models ready for use by all subsequent phases
- Source adapters (Phase 3-5) can create ArticleRef instances
- Extraction (Phase 7) can enrich to Article via model_copy(update={"full_text": ...})
- Phase 2 Plan 2 (geographic data) can proceed independently

## Self-Check: PASSED

- [x] src/models/article.py exists
- [x] src/models/__init__.py exists
- [x] Commit e26c911 exists
- [x] Commit 8fd8f6a exists

---
*Phase: 02-data-models-and-geographic-data*
*Completed: 2026-02-10*
