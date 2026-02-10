---
phase: 06-query-engine-and-scheduling
verified: 2026-02-10T12:30:00Z
status: passed
score: 5/5 must-haves verified
must_haves:
  truths:
    - "The query engine generates heat term + location queries for all 36 states/UTs across relevant languages"
    - "District-level queries use smart batching (multiple districts per query) to stay within API limits"
    - "Hierarchical querying works: state-level queries execute first, district-level queries follow for states with active results"
    - "The rate-limit-aware scheduler distributes queries across Google News RSS, NewsData.io, and GNews based on each source's capacity"
    - "Queries execute asynchronously using asyncio.TaskGroup, processing multiple sources/states in parallel"
  artifacts:
    - path: "src/query/_models.py"
      provides: "Query and QueryResult frozen dataclasses, build_category_query, build_broad_query, batch_districts"
    - path: "src/query/_generator.py"
      provides: "QueryGenerator with state-level and district-level query generation"
    - path: "src/query/_scheduler.py"
      provides: "SourceScheduler, PerSecondLimiter, WindowLimiter, factory functions"
    - path: "src/query/_executor.py"
      provides: "QueryExecutor with hierarchical state-then-district execution"
    - path: "src/query/__init__.py"
      provides: "Package re-exports (14 symbols)"
  key_links:
    - from: "src/query/_generator.py"
      to: "src/data/geo_loader.py"
      via: "imports StateUT"
    - from: "src/query/_generator.py"
      to: "src/data/heat_terms_loader.py"
      via: "imports get_terms_by_category, TERM_CATEGORIES, get_terms_for_language"
    - from: "src/query/_models.py"
      to: "src/models/article.py"
      via: "imports ArticleRef for QueryResult"
    - from: "src/query/_scheduler.py"
      to: "src/sources/_protocol.py"
      via: "TYPE_CHECKING import of NewsSource"
    - from: "src/query/_scheduler.py"
      to: "src/query/_models.py"
      via: "imports Query, QueryResult"
    - from: "src/query/_executor.py"
      to: "src/query/_generator.py"
      via: "imports QueryGenerator"
    - from: "src/query/_executor.py"
      to: "src/query/_scheduler.py"
      via: "imports SourceScheduler"
    - from: "src/query/_executor.py"
      to: "src/data/geo_loader.py"
      via: "imports StateUT, get_all_regions"
---

# Phase 6: Query Engine and Scheduling Verification Report

**Phase Goal:** The pipeline intelligently generates and executes queries across all sources, covering all states/districts with hierarchical batching and rate-limit awareness
**Verified:** 2026-02-10T12:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The query engine generates heat term + location queries for all 36 states/UTs across relevant languages | VERIFIED | `generate_state_queries()` produces 800 Google (8 categories x 100 state-lang pairs), 100 NewsData, 87 GNews queries across all 36 states/UTs. Verified via runtime: `Google: 800 NewsData: 100 GNews: 87` with `Total regions: 36` |
| 2 | District-level queries use smart batching (multiple districts per query) to stay within API limits | VERIFIED | `generate_district_queries()` batches UP's 75 districts into 3 Google queries (max 1080 chars vs 2000 limit) and 12 GNews queries (max 198 chars vs 200 limit). `batch_districts()` respects character limits via incremental cost tracking |
| 3 | Hierarchical querying works: state-level queries execute first, district-level queries follow for states with active results | VERIFIED | `QueryExecutor.run_collection()` has explicit Phase 1 (state queries) and Phase 2 (district queries). Phase 2 only executes for `active_regions = [r for r in regions if r.slug in active_slugs]`. Tested with mock: Rajasthan returns articles -> district queries run; UP returns nothing -> district queries skipped |
| 4 | The rate-limit-aware scheduler distributes queries across sources based on each source's capacity | VERIFIED | `SourceScheduler` enforces daily budgets (Google=unlimited, NewsData=200, GNews=100), per-second limiting (1.5/s, 10/s, 1/s), rolling windows (NewsData 30/15min), and concurrency (Google=5). Budget-exhausted sources return immediately without HTTP request (verified: 2 HTTP calls for daily_limit=2, third returns `budget_exhausted`) |
| 5 | Queries execute asynchronously using asyncio.TaskGroup, processing multiple sources in parallel | VERIFIED | `_execute_queries_parallel` uses `async with asyncio.TaskGroup() as tg:` with `tg.create_task()` per source. `run_collection` is `async def`. `except* Exception` handles ExceptionGroups robustly. All confirmed via source inspection and runtime test |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/query/_models.py` | Query/QueryResult dataclasses + query builders | VERIFIED | 177 lines. Frozen `Query` dataclass (8 fields incl. `source_hint`, `level`, `districts`), frozen `QueryResult` (5 fields). `build_category_query`, `build_broad_query` (char-limit aware), `batch_districts` (multi-query batching). Multi-word terms properly quoted. |
| `src/query/_generator.py` | QueryGenerator with state/district generation | VERIFIED | 229 lines. `QueryGenerator.generate_state_queries()` returns dict keyed by source hint. `generate_district_queries()` with `source_hint` parameter, `_CHAR_LIMITS` dict, `GNEWS_SUPPORTED_LANGUAGES` constant. Sorted category iteration for determinism. |
| `src/query/_scheduler.py` | SourceScheduler + rate limiters + factory functions | VERIFIED | 299 lines. `PerSecondLimiter` (asyncio.Lock, monotonic time, jitter). `WindowLimiter` (rolling window with pruning). `SourceScheduler` (budget, language filter, semaphore, never-raises). Three factory functions with correct per-source configs. |
| `src/query/_executor.py` | QueryExecutor with hierarchical execution | VERIFIED | 222 lines. `run_collection()` with two-phase execution. `_execute_queries_parallel()` with `asyncio.TaskGroup`. `_execute_query_list()` with early budget-exhaustion break. Proper logging at INFO/DEBUG levels. |
| `src/query/__init__.py` | Package re-exports (14 symbols) | VERIFIED | 54 lines. All 14 symbols exported: Query, QueryResult, build_category_query, build_broad_query, batch_districts, QueryGenerator, GNEWS_SUPPORTED_LANGUAGES, SourceScheduler, PerSecondLimiter, WindowLimiter, create_google_scheduler, create_newsdata_scheduler, create_gnews_scheduler, QueryExecutor. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_generator.py` | `src/data/geo_loader.py` | `from src.data.geo_loader import StateUT` | WIRED | Line 16. StateUT used as parameter type for both methods |
| `_generator.py` | `src/data/heat_terms_loader.py` | `from src.data.heat_terms_loader import TERM_CATEGORIES, get_terms_by_category, get_terms_for_language` | WIRED | Lines 17-21. All three used in query generation logic |
| `_models.py` | `src/models/article.py` | `from src.models.article import ArticleRef` | WIRED | Line 13. ArticleRef used as field type in QueryResult.articles |
| `_scheduler.py` | `src/sources/_protocol.py` | `TYPE_CHECKING: from src.sources._protocol import NewsSource` | WIRED | Lines 24-25. Used as type hint for source parameter |
| `_scheduler.py` | `_models.py` | `from ._models import Query, QueryResult` | WIRED | Line 22. Both used in execute() method signature and return |
| `_executor.py` | `_generator.py` | `from ._generator import QueryGenerator` | WIRED | Line 22. Used in constructor and run_collection() |
| `_executor.py` | `_scheduler.py` | `from ._scheduler import SourceScheduler` | WIRED | Line 24. Used in constructor, _execute_query_list, type hints |
| `_executor.py` | `src/data/geo_loader.py` | `from src.data.geo_loader import StateUT, get_all_regions` | WIRED | Line 19. get_all_regions called when regions=None |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| COLL-01: Pipeline queries all 36 states/UTs daily | SATISFIED | QueryGenerator.generate_state_queries() covers all 36 states/UTs. Verified: 36 regions loaded, 800+100+87 queries generated |
| COLL-02: Pipeline queries ~770 districts with smart batching | SATISFIED | generate_district_queries() batches districts within char limits. UP (75 districts) -> 3 Google queries, 12 GNews queries. All under source char limits |
| COLL-03: Hierarchical querying -- states first, districts for active states | SATISFIED | run_collection() Phase 1 does state queries, builds active_slugs set, Phase 2 filters to active_regions only |
| COLL-08: Rate-limit-aware scheduler distributes across sources | SATISFIED | SourceScheduler with per-source daily limits, per-second limiters, window limiters, and concurrency. Three factory functions preconfigure each source correctly |
| AUTO-05: Async I/O to process multiple sources in parallel | SATISFIED | asyncio.TaskGroup in _execute_queries_parallel(), async def run_collection(), PerSecondLimiter/WindowLimiter use asyncio.sleep |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

No TODO/FIXME/PLACEHOLDER comments found. No stub implementations. The single `return []` in `_models.py:149` is a valid empty-input guard for `batch_districts()`, not a stub.

### Human Verification Required

### 1. End-to-End Collection with Real APIs

**Test:** Run `QueryExecutor.run_collection()` with real Google News, NewsData.io, and GNews sources against a small subset of states during an active heat period.
**Expected:** Articles collected from multiple sources, hierarchical execution visible in logs (state queries -> active state identification -> district queries for active states).
**Why human:** Requires live API keys, real network conditions, and active heat news to verify the full pipeline produces meaningful results.

### 2. Rate Limit Behavior Under Load

**Test:** Run the full 987 state-level queries against Google News RSS and observe request pacing.
**Expected:** Google queries execute at ~1.5/s with 5-concurrent requests. NewsData stays within 30/15min window. GNews stays at 1/s.
**Why human:** Timing behavior and rate limiting correctness can only be observed in real-time execution with actual network latency.

### 3. Budget Exhaustion During District Phase

**Test:** Start a collection with GNews (100/day budget) and enough state-level queries to consume most of the budget, then observe district phase behavior.
**Expected:** GNews skips district queries when budget is exhausted, while Google continues district queries since it has unlimited budget.
**Why human:** Requires real API execution to observe budget depletion across phases.

### Gaps Summary

No gaps found. All 5 observable truths are verified. All 5 artifacts exist, are substantive implementations (not stubs), and are properly wired together. All 8 key links are confirmed via import analysis. All 5 requirements (COLL-01, COLL-02, COLL-03, COLL-08, AUTO-05) are satisfied. No anti-patterns detected. The phase goal -- intelligent query generation and execution with hierarchical batching and rate-limit awareness -- is achieved.

---

_Verified: 2026-02-10T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
