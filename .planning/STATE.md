# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** Capture every heat-related news report from every corner of India, in every language, every day -- high recall over high precision.
**Current focus:** Phase 8 - Relevance Scoring

## Current Position

Phase: 8 of 10 (Relevance Scoring)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-02-11 -- Phase 7 complete (article extraction)

Progress: [████████░░] 70%

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 3min
- Total execution time: 0.53 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-project-foundation | 1 | 2min | 2min |
| 02-data-models-and-geographic-data | 2 | 6min | 3min |
| 03-heat-terms-dictionary | 2 | 8min | 4min |
| 04-google-news-rss-source | 1 | 3min | 3min |
| 05-secondary-news-sources | 2 | 4min | 2min |
| 06-query-engine-and-scheduling | 3 | 7min | 2.3min |
| 07-article-extraction | 1 | 2min | 2min |

**Recent Trend:**
- Last 5 plans: 05-02 (2min), 06-01 (3min), 06-02 (2min), 06-03 (2min), 07-01 (2min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 10-phase comprehensive roadmap derived from 38 requirements across 10 categories
- [Roadmap]: Phases 4 and 7 can proceed in parallel (extraction only needs source interface, not all sources)
- [Roadmap]: State-level queries guaranteed before districts (RELI-05 in Phase 9, but scheduling respects this in Phase 6)
- [01-01]: Async entry point from day one -- asyncio.run(main()) avoids future refactoring
- [01-01]: Exact version pinning (==) for all 6 dependencies for reproducible builds
- [01-01]: Zero browser automation libraries -- lightweight HTTP-only approach
- [02-01]: Two-model pattern (ArticleRef -> Article) to support pipeline lifecycle stages
- [02-01]: BeforeValidator coerces naive datetimes to IST rather than rejecting them
- [02-01]: str type for url field instead of HttpUrl to handle unusual Google News URL schemes
- [02-01]: Language field constrained to 14 codes via regex pattern
- [02-02]: 725 districts from sab99r source (actual count vs plan estimate of 770+) -- data is complete
- [02-02]: Replaced mni/lus with ["en", "hi"] for Manipur/Mizoram (unsupported language codes)
- [02-02]: Frozen Pydantic models with lru_cache for single disk read per process
- [02-02]: Path(__file__).parent for working-directory-independent file loading
- [03-01]: 53 English terms and 71 Hindi terms extracted from research (high recall principle)
- [03-01]: 10 borrowed English terms in Hindi Devanagari (heat wave, heat stroke, load shedding, alerts, etc.)
- [03-01]: Suppressed Pydantic UserWarning for 'register' field name -- benign shadow of BaseModel method
- [03-02]: 564 total terms across 14 languages (high recall principle, all confidence levels included)
- [03-02]: Borrowed English terms transliterated in native script for every regional language
- [03-02]: Urdu terms exclusively in Nastaliq/Arabic script, never Devanagari
- [04-01]: typing.Protocol (structural subtyping) over abc.ABC for source interface -- no inheritance required
- [04-01]: ceid parameter uses base language code (IN:en not IN:en-IN) to avoid Google News 302 redirects
- [04-01]: follow_redirects=True on httpx.AsyncClient for robustness against Google News URL normalization
- [04-01]: Google News redirect URLs stored as-is in ArticleRef.url -- resolution deferred to Phase 7
- [04-01]: Lazy httpx.AsyncClient creation with async context manager for clean lifecycle
- [05-01]: All 14 Indian language codes in NewsDataSource _SUPPORTED_LANGUAGES (high recall principle)
- [05-01]: In-memory daily quota counter (200/day) -- no persistence needed for daily batch pipeline
- [05-01]: No follow_redirects on NewsDataSource httpx client (REST API does not redirect)
- [05-01]: Handle NewsData.io HTTP 200 error responses (status=error) alongside standard HTTP errors
- [05-01]: _daily_count incremented after request but before parsing (counts API credit, not result)
- [05-02]: Only 8 languages in GNewsSource _SUPPORTED_LANGUAGES (en, hi, bn, ta, te, mr, ml, pa) -- GNews does NOT support gu, kn, or, as, ur, ne
- [05-02]: In-memory daily quota counter (100/day) for GNews -- same pattern as NewsDataSource
- [05-02]: HTTP 403 = quota exhausted in GNews (not auth error) -- sets _daily_count = _daily_limit
- [05-02]: No follow_redirects on GNewsSource httpx client (REST API does not redirect)
- [05-02]: _daily_count incremented after request but before parsing (same pattern as NewsDataSource)
- [06-01]: Frozen dataclasses (not Pydantic) for Query/QueryResult -- internal objects, no I/O boundary validation needed
- [06-01]: Sorted TERM_CATEGORIES iteration for deterministic query ordering across runs
- [06-01]: First heatwave category term as primary heat term for district batching (most productive category)
- [06-01]: GNEWS_SUPPORTED_LANGUAGES duplicated as constant to avoid circular imports from src.sources
- [06-02]: TYPE_CHECKING import for NewsSource Protocol to avoid circular import at runtime
- [06-02]: success=True with error field for expected skip conditions (budget exhausted, unsupported language) vs success=False for actual failures
- [06-02]: Daily count incremented after HTTP request but before result processing (counts API credit, not successful parse)
- [06-02]: time.monotonic() for all rate limiting timing (immune to wall-clock adjustments)
- [06-03]: asyncio.TaskGroup for concurrent source execution with except* ExceptionGroup for robustness
- [06-03]: Sequential queries within source, concurrent across sources (scheduler handles internal rate limiting)
- [06-03]: Budget check before district query generation (not just before execution)
- [06-03]: Flat ArticleRef list return -- no nested structure, consumer just iterates
- [07-01]: XPath (tree.xpath) over cssselect for lxml HTML parsing -- avoids cssselect import issues
- [07-01]: asyncio.to_thread over run_in_executor for trafilatura sync-to-async bridge -- simpler API
- [07-01]: Shared httpx.AsyncClient per batch for connection pooling (created inside extract_articles)
- [07-01]: relevance_score=0.0 default for all Articles -- Phase 8 sets the actual score

### Pending Todos

None yet.

### Blockers/Concerns

- Research verification items still open: NewsData.io free tier limits, GNews free tier limits, Google News RSS rate limiting from GitHub Actions IPs
- Heat season approaching -- need working v1 ASAP

## Session Continuity

Last session: 2026-02-11
Stopped at: Completed 07-01-PLAN.md (article extraction). Phase 7 complete. Ready for Phase 8.
Resume file: None
