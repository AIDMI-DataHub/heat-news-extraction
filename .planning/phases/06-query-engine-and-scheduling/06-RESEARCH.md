# Phase 6: Query Engine and Scheduling - Research

**Researched:** 2026-02-10
**Domain:** Async query orchestration, rate-limited API scheduling, hierarchical search strategy
**Confidence:** HIGH

## Summary

Phase 6 is the orchestration heart of the pipeline. It must generate search queries from 564 heat terms across 14 languages and 36 states (100 state-language pairs), execute them against three news sources with vastly different rate limits (Google News RSS unlimited, NewsData.io 200/day with 30/15min window, GNews 100/day at 1/sec), and implement hierarchical querying where state-level results determine which districts get drill-down queries.

The critical insight from this research is that the three sources have fundamentally different query budgets and constraints, requiring a differentiated strategy rather than uniform treatment. Google News RSS is the workhorse (800+ queries using category-based OR-combining), while NewsData.io and GNews are supplementary (100 and 87 broad queries respectively). The 45-minute pipeline budget (from Phase 10) is achievable because the sources can execute in parallel, with NewsData.io's 15-minute rolling window being the time-dominating constraint at ~30 minutes wall time.

The query engine decomposes into three clean responsibilities: (1) a query generator that combines heat terms with location names into API-ready query strings, (2) a rate-limit-aware scheduler that manages per-source budgets and timing, and (3) an async execution engine that runs hierarchical state-then-district queries across all sources in parallel.

**Primary recommendation:** Build a `QueryGenerator` that produces `Query` dataclasses (query string, language, state, level), a per-source `RateLimiter` using `asyncio.Semaphore` + time-based throttling, and a `QueryExecutor` that runs state-level queries first across all sources in parallel, collects "active" states, then generates and executes district-level queries for those states only.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio | stdlib | Async orchestration, Semaphore, TaskGroup | Built-in, no dependencies |
| httpx | (existing) | Async HTTP (already in source adapters) | Already chosen in Phase 1 |
| dataclasses | stdlib | Query/ScheduleEntry value objects | Lightweight, no Pydantic overhead for internal objects |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Semaphore | stdlib | Concurrency limiting per source | Limit concurrent requests to each source |
| asyncio.Queue | stdlib | Work queue for query tasks | Feed queries to worker coroutines |
| time.monotonic | stdlib | Rate limit timing | Track request intervals for per-second limits |
| logging | stdlib | Query execution telemetry | Already used by all source adapters |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.Semaphore | aiolimiter (token bucket) | External dep for cleaner rate limiting, but Semaphore + sleep is sufficient |
| dataclasses | Pydantic | Pydantic adds validation overhead for high-volume internal objects; reserve for I/O boundaries |
| asyncio.TaskGroup | asyncio.gather | TaskGroup (3.11+) has better error handling and auto-cancellation; preferred |

**Installation:**
```bash
# No new dependencies needed -- all stdlib + existing httpx
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  query/
    __init__.py         # Re-exports
    _generator.py       # QueryGenerator: terms + locations -> Query objects
    _scheduler.py       # SourceScheduler: rate-limit-aware query dispatch
    _executor.py        # QueryExecutor: async hierarchical execution engine
    _models.py          # Query, QueryResult, SourceBudget dataclasses
```

### Pattern 1: Query Generation (Terms x Locations -> Query Objects)
**What:** A pure function that takes geographic data + heat terms and produces a flat list of `Query` objects ready for execution.
**When to use:** At pipeline start, before any network I/O.
**Key insight:** Each source needs different query granularity:
- Google News: 8 category queries per state-language pair (all terms OR-combined within category)
- NewsData.io: 1 broad query per state-language pair (top terms across categories, 512 char limit)
- GNews: 1 broad query per state-language pair (top terms, 200 char limit)

```python
@dataclass(frozen=True)
class Query:
    """A single search query ready for execution."""
    query_string: str      # The actual search text
    language: str          # ISO 639-1 code
    state: str             # State/UT name
    state_slug: str        # For result tracking
    level: Literal["state", "district"]
    category: str | None   # heat term category (for Google News category queries)
    districts: tuple[str, ...] = ()  # district names if level == "district"

@dataclass(frozen=True)
class QueryResult:
    """Result of executing a query against one source."""
    query: Query
    source_name: str
    articles: list[ArticleRef]
    success: bool
    error: str | None = None
```

**Query string construction rules:**
- State-level: `"(term1 OR term2 OR term3) state_name"`
- District-level: `"heat_term (District1 OR District2 OR District3)"`
- Parentheses prevent OR from applying to state name
- Quote multi-word terms: `"heat wave"` not `heat wave`

### Pattern 2: Rate-Limit-Aware Source Scheduler
**What:** Each source gets its own rate limiter that tracks daily budget, per-second limits, and per-window limits.
**When to use:** Wraps every `source.search()` call.

```python
class SourceScheduler:
    """Rate-limit-aware wrapper around a NewsSource."""

    def __init__(
        self,
        source: NewsSource,
        name: str,
        daily_limit: int | None,     # None = unlimited (Google News)
        per_second: float,            # Max requests per second
        window_limit: int | None = None,  # E.g., 30 for NewsData.io
        window_seconds: int = 900,    # 15 min = 900s
    ):
        self._source = source
        self._name = name
        self._daily_limit = daily_limit
        self._daily_count = 0
        self._per_second = per_second
        self._semaphore = asyncio.Semaphore(1)  # serialize per source
        self._last_request_time = 0.0
        self._window_limit = window_limit
        self._window_count = 0
        self._window_start = 0.0

    async def execute(self, query: Query) -> QueryResult:
        """Execute query with rate limiting. Returns result, never raises."""
        if self._is_budget_exhausted():
            return QueryResult(query=query, source_name=self._name,
                             articles=[], success=True, error="budget_exhausted")

        async with self._semaphore:
            await self._wait_for_rate_limit()
            articles = await self._source.search(
                query.query_string, query.language,
                state=query.state, search_term=query.query_string,
            )
            self._record_request()
            return QueryResult(query=query, source_name=self._name,
                             articles=articles, success=True)

    @property
    def remaining_budget(self) -> int | None:
        if self._daily_limit is None:
            return None
        return max(0, self._daily_limit - self._daily_count)
```

### Pattern 3: Hierarchical Execution (State-First, Then District Drill-Down)
**What:** Execute all state-level queries first across all sources in parallel. Collect which states had results (are "active"). Then generate district-level queries only for active states.
**When to use:** This IS the main execution flow.

```python
async def run_collection(sources: list[SourceScheduler], regions: list[StateUT]) -> list[ArticleRef]:
    # Phase 1: State-level queries
    state_queries = generate_state_queries(regions)
    state_results = await execute_queries_parallel(sources, state_queries)

    # Identify active states (those that returned articles)
    active_slugs = {r.query.state_slug for r in state_results if r.articles}

    # Phase 2: District-level queries (only for active states)
    active_regions = [r for r in regions if r.slug in active_slugs]
    district_queries = generate_district_queries(active_regions)
    district_results = await execute_queries_parallel(sources, district_queries)

    # Combine all articles
    all_articles = []
    for r in state_results + district_results:
        all_articles.extend(r.articles)
    return all_articles
```

### Pattern 4: Parallel Multi-Source Execution with asyncio.TaskGroup
**What:** For each query, dispatch to all eligible sources concurrently. Use TaskGroup for structured concurrency.
**When to use:** When executing a batch of queries.

```python
async def execute_queries_parallel(
    schedulers: list[SourceScheduler],
    queries: list[Query],
) -> list[QueryResult]:
    results: list[QueryResult] = []

    async with asyncio.TaskGroup() as tg:
        for query in queries:
            for scheduler in schedulers:
                if scheduler.supports_language(query.language):
                    task = tg.create_task(scheduler.execute(query))
                    # Collect results via callback or post-processing

    return results
```

**Important:** TaskGroup cancels all tasks if any raises. Since source adapters never raise (return empty list on error), this is safe. But wrap in try/except* as defense.

### Anti-Patterns to Avoid
- **One query per term:** With 564 terms x 100 state-lang pairs = 56,400 queries. Must OR-combine terms.
- **Uniform query strategy across sources:** Each source has different limits; treat them differently.
- **Sequential source execution:** Sources have independent rate limits; run in parallel.
- **Ignoring the 15-minute window for NewsData.io:** Bursting all 200 requests will trigger rate limiting after 30.
- **District queries for all states:** Most states won't have active heat news. Only drill down for states with results.
- **Blocking on NewsData.io waits:** While waiting for the 15-min window to reset, Google News and GNews queries should continue.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-second rate limiting | Custom sleep loop | `asyncio.Semaphore` + `asyncio.sleep` with `time.monotonic()` | Edge cases with clock drift, concurrent access |
| Query string length validation | Manual char counting | Pre-compute and validate during query generation | Runtime failures are harder to debug than generation-time checks |
| Result deduplication | Custom dedup in executor | Defer to Phase 8 | Phase 6 collects; Phase 8 deduplicates |

**Key insight:** The query engine should focus on generation and execution. Deduplication, filtering, and scoring are Phase 8 concerns. Phase 6 should collect aggressively and pass everything downstream.

## Common Pitfalls

### Pitfall 1: NewsData.io 15-Minute Rolling Window
**What goes wrong:** Firing 200 requests rapidly triggers rate limiting after 30 requests, causing 170 wasted quota entries that return errors.
**Why it happens:** The 30 credits/15-minute rolling window is tighter than the 200/day limit.
**How to avoid:** Track window start time. After 30 requests, compute remaining wait time in the current 15-minute window. Use `asyncio.sleep()` to wait, then continue.
**Warning signs:** HTTP 429 responses from NewsData.io, or `status: error` responses with rate limit messages.

### Pitfall 2: Google News RSS Soft Rate Limiting
**What goes wrong:** Google returns 429 or CAPTCHAs after too many rapid requests, even though there's no formal daily limit.
**Why it happens:** Google uses undocumented rate limiting that varies. Community testing suggests ~100 requests/hour is safe.
**How to avoid:** Use `asyncio.Semaphore(5)` to limit concurrency and add 0.5-1.0 second delays with jitter between requests. Implement exponential backoff on 429 responses.
**Warning signs:** HTTP 429 responses, empty RSS feeds, CAPTCHA pages in response body.

### Pitfall 3: OR Operator Semantics Differ Between APIs
**What goes wrong:** Query `"heatwave OR Rajasthan"` returns results about heatwaves OR results about Rajasthan (unrelated news about Rajasthan).
**Why it happens:** OR applies across all terms. Need parenthetical grouping.
**How to avoid:** Always use parentheses: `"(heatwave OR heat wave) Rajasthan"`. This means: articles containing (heatwave OR heat wave) AND Rajasthan.
**Warning signs:** Getting cricket news from Rajasthan, general Rajasthan news without heat context.

### Pitfall 4: Multi-Word District Names with OR
**What goes wrong:** `"heatwave Ambedkar Nagar OR Lucknow"` is parsed as `"heatwave Ambedkar (Nagar OR Lucknow)"`.
**Why it happens:** OR binds tighter than space-separated terms.
**How to avoid:** Quote multi-word names: `"heatwave \"Ambedkar Nagar\" OR \"Lucknow\""` or use parenthetical grouping: `"heatwave (\"Ambedkar Nagar\" OR Lucknow)"`.
**Warning signs:** Unexpected results, missing districts from results.

### Pitfall 5: Exhausting Supplementary Budgets on Low-Value Queries
**What goes wrong:** NewsData.io's 200 credits are spent on states that Google News already covered well, leaving nothing for unique coverage.
**Why it happens:** No prioritization -- queries processed in alphabetical order.
**How to avoid:** Prioritize NewsData.io/GNews queries for: (1) languages where Google News coverage is weaker, (2) states with high heat risk. Use Google News as the comprehensive sweep; supplementary sources for gap-filling.
**Warning signs:** NewsData/GNews budget exhausted but many state-language pairs uncovered.

### Pitfall 6: asyncio.TaskGroup Cancellation on Error
**What goes wrong:** One source's unexpected exception cancels all other running queries.
**Why it happens:** TaskGroup cancels remaining tasks when any task raises (unlike `gather(return_exceptions=True)`).
**How to avoid:** Source adapters already never raise (return empty list). Add a defensive wrapper in the scheduler that catches any unexpected exception and returns an error QueryResult instead of raising.
**Warning signs:** Entire collection run failing when a single source has issues.

## Code Examples

### Query String Construction

```python
def build_category_query(terms: list[str], location: str) -> str:
    """Build a category-based query: (term1 OR term2 OR ...) location.

    Multi-word terms are quoted to prevent OR from splitting them.
    """
    quoted = []
    for t in terms:
        if " " in t:
            quoted.append(f'"{t}"')
        else:
            quoted.append(t)
    terms_part = " OR ".join(quoted)
    return f"({terms_part}) {location}"


def build_broad_query(terms: list[str], location: str, max_chars: int) -> str:
    """Build a broad query fitting within max_chars limit.

    Picks highest-priority terms that fit within the character budget.
    Terms are assumed to be ordered by priority (most important first).
    """
    overhead = len(location) + 3  # space + parens
    budget = max_chars - overhead
    selected = []
    used = 0
    for t in terms:
        term_repr = f'"{t}"' if " " in t else t
        cost = len(term_repr) + (4 if selected else 0)  # " OR " separator
        if used + cost > budget:
            break
        selected.append(term_repr)
        used += cost
    if not selected:
        selected = [terms[0][:budget]]  # Truncate single term as last resort
    terms_part = " OR ".join(selected)
    return f"({terms_part}) {location}"
```

### District Batching

```python
def batch_districts(
    districts: list[District],
    heat_term: str,
    max_chars: int,
) -> list[str]:
    """Batch district names into query strings within max_chars limit.

    Returns list of query strings, each containing as many districts
    as will fit within the character budget.
    """
    queries = []
    overhead = len(heat_term) + 3  # "heat_term (" + ")"
    budget = max_chars - overhead

    batch: list[str] = []
    used = 0
    for d in districts:
        name = f'"{d.name}"' if " " in d.name else d.name
        cost = len(name) + (4 if batch else 0)  # " OR "
        if used + cost > budget and batch:
            query = f'{heat_term} ({" OR ".join(batch)})'
            queries.append(query)
            batch = [name]
            used = len(name)
        else:
            batch.append(name)
            used += cost

    if batch:
        query = f'{heat_term} ({" OR ".join(batch)})'
        queries.append(query)

    return queries
```

### Rate-Limited Async Execution

```python
import asyncio
import time

class PerSecondLimiter:
    """Simple per-second rate limiter using asyncio."""

    def __init__(self, max_per_second: float):
        self._interval = 1.0 / max_per_second
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._last + self._interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class WindowLimiter:
    """Rolling window rate limiter (e.g., 30 requests per 15 minutes)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max = max_requests
        self._window = window_seconds
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        now = time.monotonic()
        # Remove timestamps outside current window
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        if len(self._timestamps) >= self._max:
            # Wait until oldest timestamp exits the window
            wait = self._timestamps[0] + self._window - now + 0.1
            await asyncio.sleep(wait)
            self._timestamps = [t for t in self._timestamps if time.monotonic() - t < self._window]
        self._timestamps.append(time.monotonic())
```

### Hierarchical Execution Flow

```python
async def collect_articles(
    google: SourceScheduler,
    newsdata: SourceScheduler,
    gnews: SourceScheduler,
    regions: list[StateUT],
) -> list[ArticleRef]:
    """Main collection flow: state-level first, then district drill-down."""

    all_articles: list[ArticleRef] = []

    # --- Phase 1: State-level queries ---
    state_queries = generate_state_level_queries(regions)
    logger.info("Executing %d state-level queries", len(state_queries))

    # Run all sources in parallel via TaskGroup
    state_results = await execute_across_sources(
        [google, newsdata, gnews], state_queries
    )
    all_articles.extend(
        article for r in state_results for article in r.articles
    )

    # --- Determine active states ---
    active_slugs: set[str] = set()
    for result in state_results:
        if result.articles:
            active_slugs.add(result.query.state_slug)
    logger.info(
        "%d / %d states have active heat news",
        len(active_slugs), len(regions),
    )

    # --- Phase 2: District-level queries (active states only) ---
    active_regions = [r for r in regions if r.slug in active_slugs]
    district_queries = generate_district_level_queries(active_regions)
    logger.info("Executing %d district-level queries", len(district_queries))

    district_results = await execute_across_sources(
        [google, newsdata, gnews], district_queries
    )
    all_articles.extend(
        article for r in district_results for article in r.articles
    )

    logger.info("Total articles collected: %d", len(all_articles))
    return all_articles
```

## Query Volume Analysis (Verified from Actual Data)

### Source Data Dimensions
| Dimension | Count | Detail |
|-----------|-------|--------|
| States/UTs | 36 | 28 states + 8 union territories |
| Districts | 725 | Range: 1 (Chandigarh) to 75 (Uttar Pradesh) |
| Languages | 14 | en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne |
| State-Language pairs | 100 | Each state maps to 2-4 languages (avg 2.8) |
| Total heat terms | 564 | Range: 29 (Assamese) to 71 (Hindi) per language |
| Term categories | 8 | heatwave, death_stroke, water_crisis, power_cuts, crop_damage, human_impact, government_response, temperature |

### Per-Source Query Budget

| Source | Daily Limit | Per-Second | Per-15-Min | Languages | State-Level Queries | District Budget |
|--------|------------|------------|------------|-----------|--------------------|----|
| Google News RSS | Unlimited (~100/hr safe) | ~1.5 with jitter | N/A | 14 | 800 (8 categories x 100 pairs) | ~300 (active states) |
| NewsData.io | 200 | 10 | 30 | 14 | 100 (1 broad per pair) | 100 remaining |
| GNews | 100 | 1 | N/A | 8 | 87 (1 broad per pair, 8 langs) | 13 remaining |

### API Query String Limits (Verified)

| API | Max Query Length | Operators Supported | Source |
|-----|-----------------|---------------------|--------|
| Google News RSS | ~2048 (URL limit) | Implicit AND, OR, quotes | URL-encoded query param |
| NewsData.io | 512 characters | AND, OR, NOT, quotes, parens | [Official docs](https://newsdata.io/blog/how-do-q-qintitle-qinmeta-works/) |
| GNews | 200 characters | AND, OR, NOT, quotes | [Official docs](https://docs.gnews.io/endpoints/search-endpoint) |

### District Batching Capacity
| API | Districts per Query | Queries for UP (75 districts) | Queries for Rajasthan (33 districts) |
|-----|--------------------|----|-----|
| Google News RSS | ~30 | 3 | 2 |
| NewsData.io (512 chars) | ~35 | 3 per lang | 1 per lang |
| GNews (200 chars) | ~10 | 8 per lang | 4 per lang |

### Time Budget (within 45-minute pipeline)
| Source | Strategy | Wall Time | Notes |
|--------|----------|-----------|-------|
| Google News RSS | 5 concurrent workers, 1 req/s each | ~5-8 min | Fastest, most comprehensive |
| GNews | Sequential 1 req/s | ~2 min | Small budget, fast |
| NewsData.io | 30-request bursts with 15-min waits | ~30 min | Time-dominating constraint |
| **Total (parallel)** | All sources run concurrently | **~30 min** | Leaves 15 min for extraction/dedup |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.gather()` | `asyncio.TaskGroup` | Python 3.11 (Oct 2022) | Better error handling, auto-cancellation |
| `aiohttp` | `httpx` (async) | Already decided Phase 1 | Unified sync/async client, already in codebase |
| External rate limiter libs | stdlib Semaphore + monotonic time | N/A | Zero additional dependencies |
| `abc.ABC` interfaces | `typing.Protocol` | Already decided Phase 4 | Structural subtyping, no inheritance needed |

**Deprecated/outdated:**
- `pygooglenews`: Unmaintained since 2021, already rejected in Phase 4
- `asyncio.gather(return_exceptions=True)`: Works but TaskGroup is cleaner for structured concurrency

## Open Questions

1. **Google News safe request rate**
   - What we know: Community testing suggests ~100 req/hr. No official docs.
   - What's unclear: Exact threshold before 429/CAPTCHA triggers. May vary by IP/time.
   - Recommendation: Start conservative at 5 concurrent with 0.7s delay (~7 req/s burst within semaphore). Back off on any 429. Monitor in Phase 10 integration testing.

2. **Optimal category selection for supplementary sources**
   - What we know: With 100 NewsData.io queries for state-level, we can only use 1 broad query per state-language pair. Need to pick the most productive terms.
   - What's unclear: Which categories yield the most heat news results in practice.
   - Recommendation: Default priority order: heatwave > temperature > death_stroke > water_crisis. This can be made configurable. During initial runs, log which categories produce the most results to tune later.

3. **How many states will be "active" on a typical day?**
   - What we know: India's heat season (March-June) affects different regions at different times. Off-season, very few states will have heat news.
   - What's unclear: Exact ratio of active to inactive states.
   - Recommendation: Design for 10-20 active states during peak season, 2-5 during off-season. District query budget scales dynamically based on actual active count.

4. **NewsData.io effective capacity in 45-minute window**
   - What we know: 30 credits per 15-minute rolling window. In 45 min, theoretically 90 credits.
   - What's unclear: Whether the window is strictly rolling or resets at fixed intervals.
   - Recommendation: Implement as rolling window with conservative tracking. In worst case, 90 of 200 daily credits used in a single run. The remaining 110 are lost (no multi-run-per-day architecture yet).

## Sources

### Primary (HIGH confidence)
- `src/data/india_geo.json` -- 36 states, 725 districts, language mappings (verified via code analysis)
- `src/data/heat_terms.json` -- 564 terms across 14 languages (verified via code analysis)
- `src/sources/google_news.py` -- GoogleNewsSource implementation, no daily limit
- `src/sources/newsdata.py` -- NewsDataSource, 200/day limit, 14 languages
- `src/sources/gnews.py` -- GNewsSource, 100/day limit, 8 languages
- `src/sources/_protocol.py` -- NewsSource Protocol interface
- [NewsData.io query docs](https://newsdata.io/blog/how-do-q-qintitle-qinmeta-works/) -- 512 char limit, AND/OR/NOT operators
- [NewsData.io rate limits](https://newsdata.io/blog/newsdata-rate-limit/) -- 10/sec, 30/15min, 200/day
- [GNews search endpoint](https://docs.gnews.io/endpoints/search-endpoint) -- 200 char limit, AND/OR/NOT operators
- [GNews pricing](https://gnews.io/pricing) -- 100/day, 1/sec, resets at 00:00 UTC

### Secondary (MEDIUM confidence)
- [Google Search Central thread](https://support.google.com/webmasters/thread/9479430) -- No official rate limit published for RSS
- Community testing suggesting ~100 req/hr safe rate for Google News RSS

### Tertiary (LOW confidence)
- Google News RSS rate limiting behavior -- no official documentation exists; varies by IP and time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies, builds on existing source adapters
- Architecture: HIGH -- patterns are well-established async Python, verified against actual data dimensions
- Query volume math: HIGH -- computed from actual india_geo.json (725 districts) and heat_terms.json (564 terms)
- API limits: HIGH -- verified from official API documentation for NewsData.io and GNews
- Google News rate limits: LOW -- no official documentation; based on community reports
- Time budget: MEDIUM -- calculated from known rate limits, but real-world variability exists
- Pitfalls: HIGH -- derived from API documentation and known async programming patterns

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days -- API rate limits may change)
