# Phase 9: Output and Reliability - Research

**Researched:** 2026-02-11
**Domain:** Async file I/O, checkpoint/resume, circuit breakers, retry with backoff
**Confidence:** HIGH

## Summary

Phase 9 adds three orthogonal capabilities to the existing pipeline: (1) organized JSON/CSV output writers, (2) checkpoint/resume for crash recovery, and (3) reliability primitives (circuit breakers and exponential backoff). All three depend on libraries already pinned in requirements.txt -- `aiofiles` for async file I/O and `tenacity` for retry logic -- so no new dependencies are needed.

The codebase is well-structured for this work. The `src/output/` package already exists as an empty placeholder with just `__init__.py`. The pipeline currently returns flat `list[Article]` from deduplication, which needs to be grouped by state, serialized to JSON/CSV, and written to date-organized directories. The checkpoint system must integrate with `QueryExecutor.run_collection()` to track completed query batches. The circuit breaker must wrap each `SourceScheduler` independently. Tenacity retry decorators must wrap the individual source `execute()` calls for HTTP 429 backoff.

**Primary recommendation:** Build three independent modules -- `src/output/_writers.py` (JSON+CSV), `src/reliability/_checkpoint.py` (checkpoint/resume), and `src/reliability/_circuit_breaker.py` (circuit breaker + tenacity retry) -- then integrate them into the existing `QueryExecutor` and `main.py` orchestration.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiofiles | 24.1.0 | Async file I/O for JSON/CSV writes | Already pinned; prevents blocking event loop during file writes |
| tenacity | 9.0.0 | Exponential backoff with jitter for retry | Already pinned; `wait_exponential_jitter` is the exact primitive needed |
| pydantic | 2.10.6 | Article serialization via `model_dump(mode='json')` | Already in use; `mode='json'` gives JSON-serializable dicts |
| json (stdlib) | -- | JSON serialization with `ensure_ascii=False` for Indian scripts | Standard library; handles non-Latin scripts correctly |
| csv (stdlib) | -- | CSV output via `DictWriter` | Standard library; handles quoting/escaping automatically |
| pathlib (stdlib) | -- | Directory creation with `mkdir(parents=True, exist_ok=True)` | Standard library; idiomatic Python path handling |
| hashlib (stdlib) | -- | Stable query keys for checkpoint tracking | Standard library; SHA-256 truncated to 16 hex chars |
| io (stdlib) | -- | `StringIO` buffer for building CSV content before async write | Standard library; needed for csv.DictWriter -> aiofiles bridge |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiofiles for JSON writes | `asyncio.to_thread(Path.write_text, ...)` | Works but aiofiles is already pinned and more idiomatic for async I/O |
| hashlib for query keys | Frozen dataclass `__hash__` | Query dataclass hash is implementation-dependent; explicit SHA-256 is stable across Python versions |
| stdlib csv via StringIO | pandas `to_csv()` | Massive dependency for trivial CSV writing; not worth adding |
| Custom circuit breaker | pybreaker library | Extra dependency; circuit breaker is 30 lines of code for our use case |
| JSON checkpoint file | SQLite via aiosqlite | Over-engineered; checkpoint is a small JSON file updated per batch |

## Architecture Patterns

### Recommended Module Structure

```
src/
  output/
    __init__.py          # Re-exports write_json, write_csv, write_collection_output
    _writers.py          # JSON and CSV output functions
    _metadata.py         # CollectionMetadata model for OUTP-04
  reliability/
    __init__.py          # Re-exports CircuitBreaker, CheckpointStore
    _checkpoint.py       # Checkpoint save/load/resume logic
    _circuit_breaker.py  # Per-source circuit breaker
    _retry.py            # Tenacity retry decorator factory
```

### Pattern 1: Pydantic model_dump(mode='json') for Serialization

**What:** Use Pydantic's built-in `model_dump(mode='json')` to get JSON-serializable dicts from Article objects. This converts datetime objects to ISO strings automatically.

**When to use:** Any time Article objects need to be written to JSON or CSV.

**Verified behavior (tested locally):**
```python
article.model_dump(mode='json')
# Returns: {'title': '...', 'date': '2026-02-11T10:30:00+05:30', ...}
# All types are JSON-serializable (datetime -> str, None preserved)
```

**Key detail:** `model_dump()` (without `mode='json'`) returns datetime objects, which `json.dumps()` cannot serialize. Always use `mode='json'` for output.

### Pattern 2: aiofiles + StringIO Bridge for CSV

**What:** Build CSV content in a `StringIO` buffer using stdlib `csv.DictWriter`, then write the complete string via `aiofiles.open()`.

**When to use:** Any async CSV file output.

**Verified behavior (tested locally):**
```python
import csv, io, aiofiles

buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=list(articles[0].model_dump(mode='json').keys()))
writer.writeheader()
for article in articles:
    writer.writerow(article.model_dump(mode='json'))

async with aiofiles.open(path, 'w', encoding='utf-8', newline='') as f:
    await f.write(buf.getvalue())
```

**Why StringIO bridge:** `csv.DictWriter` is synchronous and writes to file-like objects. Cannot use aiofiles directly with csv.DictWriter. Build content in memory, then write atomically.

### Pattern 3: Tenacity Async Retry with Custom Predicate

**What:** Use `tenacity.retry` decorator with `retry_if_exception` and a custom predicate that checks for HTTP 429 status codes.

**When to use:** Wrapping SourceScheduler.execute() or individual source search() calls for rate limit retry.

**Verified behavior (tested locally -- tenacity 9.0.0):**
```python
import tenacity
import httpx

def is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    return False

@tenacity.retry(
    wait=tenacity.wait_exponential_jitter(initial=1, max=60, jitter=5),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception(is_rate_limit_error),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def execute_with_retry(scheduler, query):
    return await scheduler.execute(query)
```

**Critical detail:** The existing source `search()` methods catch all exceptions and return empty lists -- they never raise. The retry must happen BEFORE the source catches the exception. Two options:

- **Option A:** Add tenacity retry inside each source's `search()` method around the HTTP call only (before the catch-all). This is surgical but requires modifying 3 source files.
- **Option B:** Add a retry layer in `SourceScheduler.execute()` that catches `httpx.HTTPStatusError` with status 429 before the source's catch-all fires. Problem: the source `search()` already catches everything.

**Recommended approach:** The source `search()` methods already handle HTTP 429 by logging and returning empty lists. To add retry with backoff, the cleanest path is to modify the source `search()` methods to re-raise HTTP 429 errors (and only 429), letting a tenacity decorator on the SourceScheduler handle the retry. Alternatively, wrap just the HTTP call inside each source with tenacity.

**Simplest correct approach:** Add tenacity retry inside `SourceScheduler.execute()` as a wrapper. But since source `search()` never raises, we need the source to signal rate-limit differently. The cleanest option: create a dedicated `RateLimitError` exception, have sources raise it for HTTP 429 (instead of catching it), and let the SourceScheduler's tenacity retry handle it. This preserves the "never raises for transport errors" contract at the scheduler level while enabling retry for the specific rate-limit case.

### Pattern 4: Per-Source Circuit Breaker

**What:** A simple state machine (closed -> open -> half-open -> closed) that tracks consecutive failures per source and temporarily halts queries to that source when failures exceed a threshold.

**When to use:** Wrapping each SourceScheduler to prevent hammering a down source.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed | open | half_open

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self._reset_timeout:
                self._state = "half_open"
                return False
            return True
        return False

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "open"
```

**Integration point:** The circuit breaker checks before `SourceScheduler.execute()` calls the source. When open, it returns a `QueryResult(success=True, error="circuit_breaker_open")` (same pattern as budget_exhausted -- expected skip, not failure).

### Pattern 5: JSON Checkpoint for Query Batch Tracking

**What:** A JSON file that records which query batches have been completed. On restart, the pipeline loads the checkpoint and skips already-completed queries.

**When to use:** After each completed query batch in `QueryExecutor._execute_query_list()`.

```python
# Checkpoint file format
{
    "pipeline_run_id": "2026-02-11T10:30:00+05:30",
    "completed_queries": ["hash1", "hash2", ...],
    "phase": "state" | "district",
    "stats": {
        "total_queries": 100,
        "completed_queries": 45,
        "articles_found": 230
    }
}
```

**Query key generation (tested locally):**
```python
def query_key(q: Query) -> str:
    raw = f'{q.source_hint}|{q.state_slug}|{q.language}|{q.level}|{q.query_string}'
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

**Integration point:** `QueryExecutor` receives a `CheckpointStore` instance. Before executing each query, it checks if the query key is in the checkpoint. After successful execution, it adds the key and saves.

### Pattern 6: Output Directory Structure

**What:** Date-based directory organization with state subdirectories.

```
output/
  2026-02-11/
    rajasthan/
      articles.json
      articles.csv
    maharashtra/
      articles.json
      articles.csv
    ...
    _metadata.json    # Collection-level metadata (OUTP-04)
```

**Directory creation on write (OUTP-03):** Use `pathlib.Path.mkdir(parents=True, exist_ok=True)` before writing. Never pre-create directories.

**JSON structure per state file:**
```json
{
    "state": "Rajasthan",
    "date": "2026-02-11",
    "article_count": 15,
    "articles": [
        {
            "title": "...",
            "url": "...",
            "source": "...",
            "date": "2026-02-11T10:30:00+05:30",
            "language": "en",
            "state": "Rajasthan",
            "district": "Jaipur",
            "search_term": "heatwave",
            "full_text": "...",
            "relevance_score": 0.85
        }
    ]
}
```

**Metadata structure (OUTP-04):**
```json
{
    "collection_timestamp": "2026-02-11T15:30:00+05:30",
    "sources_queried": ["google_news", "newsdata", "gnews"],
    "query_terms_used": ["heatwave", "heat stroke", ...],
    "counts": {
        "articles_found": 500,
        "articles_extracted": 420,
        "articles_filtered": 350
    }
}
```

### Anti-Patterns to Avoid

- **Pre-creating output directories:** OUTP-03 explicitly requires creation on write. Do not create a directory tree at pipeline start.
- **Synchronous file I/O in async code:** The pipeline is fully async. Using `open()` instead of `aiofiles.open()` would block the event loop during writes.
- **Global circuit breaker:** RELI-03 requires independent per-source circuit breakers. A single shared breaker would halt all sources when one fails.
- **Persisting checkpoint in memory only:** The entire point of checkpoints is crash recovery. The checkpoint must be written to disk after each batch.
- **Retrying all errors with tenacity:** Only rate-limit errors (HTTP 429) should trigger exponential backoff. Retrying auth errors (401) or quota exhaustion (403) wastes time and quota.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exponential backoff with jitter | Custom sleep loop with random delays | `tenacity.wait_exponential_jitter(initial=1, max=60, jitter=5)` | Handles edge cases (overflow, monotonic time), well-tested |
| Async retry decorator | Manual retry counter in try/except | `tenacity.retry()` with `retry_if_exception` | Handles async functions natively via `AsyncRetrying`, composable strategies |
| Retry logging | Print statements in retry loop | `tenacity.before_sleep_log(logger, logging.WARNING)` | Structured logging with attempt count and wait time |
| CSV field quoting/escaping | Manual string formatting | `csv.DictWriter` with default quoting | Handles commas, newlines, quotes in article text/titles correctly |
| JSON datetime serialization | Custom `default=` handler for `json.dumps` | `article.model_dump(mode='json')` | Pydantic handles all type conversions; datetime -> ISO string |

**Key insight:** tenacity 9.0.0 is already pinned and provides everything needed for RELI-04. The `wait_exponential_jitter` strategy is purpose-built for rate limit backoff. Writing a custom backoff loop would be strictly worse.

## Common Pitfalls

### Pitfall 1: Blocking the Event Loop with Synchronous File I/O

**What goes wrong:** Using `open()` and `json.dump()` instead of `aiofiles.open()` blocks the event loop during file writes, degrading concurrent source execution.
**Why it happens:** Habit from synchronous Python; file I/O feels "fast enough" but scales poorly with many files.
**How to avoid:** Always use `aiofiles.open()` for all file operations. Build JSON string in memory with `json.dumps()`, then write via aiofiles.
**Warning signs:** Pipeline speed drops when writing output for many states simultaneously.

### Pitfall 2: Checkpoint Race Condition with Concurrent Sources

**What goes wrong:** Multiple TaskGroup coroutines try to update the checkpoint file simultaneously, causing lost updates or corrupted JSON.
**Why it happens:** Sources execute concurrently via `asyncio.TaskGroup`. If checkpoint saves happen inside the source tasks, writes can interleave.
**How to avoid:** Checkpoint saves should happen in the sequential orchestration layer (`_execute_query_list`), not inside concurrent tasks. Alternatively, use an `asyncio.Lock` to serialize checkpoint writes.
**Warning signs:** Checkpoint file has fewer entries than expected after a run.

### Pitfall 3: CSV with full_text Containing Newlines

**What goes wrong:** Article `full_text` fields contain newlines, commas, and quotes. Naive CSV writing produces malformed output.
**Why it happens:** Real article text has complex formatting.
**How to avoid:** Use `csv.DictWriter` (not manual string formatting), which handles quoting automatically with `QUOTE_MINIMAL` (default).
**Warning signs:** CSV readers report wrong column counts.

### Pitfall 4: ensure_ascii=False Forgotten in json.dumps

**What goes wrong:** Indian language characters (Devanagari, Tamil, etc.) are escaped as `\uXXXX` in JSON output, making files unreadable.
**Why it happens:** `json.dumps()` defaults to `ensure_ascii=True`.
**How to avoid:** Always pass `ensure_ascii=False` to `json.dumps()` and specify `encoding='utf-8'` for file opens.
**Warning signs:** JSON files contain escaped Unicode instead of native script characters.

### Pitfall 5: Tenacity Retrying Non-Retriable Errors

**What goes wrong:** HTTP 401 (bad API key) or 403 (quota exhausted) errors are retried with backoff, wasting time and quota.
**Why it happens:** Using `retry_if_exception_type(httpx.HTTPStatusError)` instead of a custom predicate that checks status code.
**How to avoid:** Use `retry_if_exception(is_rate_limit_error)` with a predicate that only matches HTTP 429.
**Warning signs:** Pipeline hangs retrying a permanently-failing request.

### Pitfall 6: Circuit Breaker Interacting Badly with Rate Limiter

**What goes wrong:** Rate limiter delays plus circuit breaker timeout create confusing behavior where a source appears to recover but then immediately trips again.
**Why it happens:** Circuit breaker timeout expires during a rate limiter wait, letting through a request that immediately fails again.
**How to avoid:** Circuit breaker check should happen before rate limiter acquire (fail fast, don't wait). Reset timeout should be significantly longer than the rate limiter's maximum delay.
**Warning signs:** Source oscillates between open and half-open circuit breaker states.

### Pitfall 7: Source search() Never Raises -- Retry Has Nothing to Catch

**What goes wrong:** Tenacity retry decorator on SourceScheduler.execute() never fires because the underlying source.search() catches all exceptions and returns empty lists.
**Why it happens:** Sources were designed to "never raise" (Phase 4/5 requirement). Tenacity needs exceptions to trigger retry.
**How to avoid:** The retry must wrap the HTTP call specifically, before the source's catch-all. Options: (1) raise a `RateLimitError` from sources for 429 only, (2) apply tenacity inside each source's search() around the HTTP call only, or (3) add retry at the SourceScheduler level with a new exception type. Option 1 is cleanest.
**Warning signs:** Tenacity `before_sleep_log` never fires during runs with known rate limiting.

## Code Examples

### JSON Output Writer

```python
import json
import aiofiles
from pathlib import Path
from src.models.article import Article

async def write_json(articles: list[Article], output_dir: Path, state_slug: str) -> Path:
    """Write articles to a JSON file, creating directories on write."""
    state_dir = output_dir / state_slug
    state_dir.mkdir(parents=True, exist_ok=True)  # OUTP-03

    path = state_dir / "articles.json"
    data = {
        "state": articles[0].state if articles else state_slug,
        "date": output_dir.name,  # e.g. "2026-02-11"
        "article_count": len(articles),
        "articles": [a.model_dump(mode='json') for a in articles],
    }
    content = json.dumps(data, indent=2, ensure_ascii=False)
    async with aiofiles.open(path, 'w', encoding='utf-8') as f:
        await f.write(content)
    return path
```

### CSV Output Writer

```python
import csv
import io
import aiofiles
from pathlib import Path
from src.models.article import Article

async def write_csv(articles: list[Article], output_dir: Path, state_slug: str) -> Path:
    """Write articles to a CSV file, creating directories on write."""
    state_dir = output_dir / state_slug
    state_dir.mkdir(parents=True, exist_ok=True)

    path = state_dir / "articles.csv"
    if not articles:
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write("")
        return path

    fieldnames = list(articles[0].model_dump(mode='json').keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for article in articles:
        writer.writerow(article.model_dump(mode='json'))

    async with aiofiles.open(path, 'w', encoding='utf-8', newline='') as f:
        await f.write(buf.getvalue())
    return path
```

### Tenacity Retry for Rate Limits

```python
import tenacity
import httpx
import logging

logger = logging.getLogger(__name__)

def is_rate_limit_error(exc: BaseException) -> bool:
    """Return True only for HTTP 429 rate limit errors."""
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429

# For use as a decorator factory
def with_rate_limit_retry(max_attempts: int = 5):
    return tenacity.retry(
        wait=tenacity.wait_exponential_jitter(initial=1, max=60, jitter=5),
        stop=tenacity.stop_after_attempt(max_attempts),
        retry=tenacity.retry_if_exception(is_rate_limit_error),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
```

### Circuit Breaker Integration

```python
import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Per-source circuit breaker (closed -> open -> half_open -> closed)."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self._reset_timeout:
                self._state = "half_open"
                logger.info("%s circuit breaker: open -> half_open (testing)", self._name)
                return False
            return True
        return False

    def record_success(self) -> None:
        if self._state == "half_open":
            logger.info("%s circuit breaker: half_open -> closed (recovered)", self._name)
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "open"
            logger.warning(
                "%s circuit breaker OPEN after %d consecutive failures",
                self._name, self._failure_count,
            )
```

### Checkpoint Store

```python
import json
import hashlib
import aiofiles
from pathlib import Path
from src.query._models import Query

class CheckpointStore:
    """Saves and loads checkpoint state for crash recovery."""

    def __init__(self, checkpoint_path: Path) -> None:
        self._path = checkpoint_path
        self._completed: set[str] = set()

    @staticmethod
    def query_key(q: Query) -> str:
        raw = f'{q.source_hint}|{q.state_slug}|{q.language}|{q.level}|{q.query_string}'
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_completed(self, q: Query) -> bool:
        return self.query_key(q) in self._completed

    async def mark_completed(self, q: Query) -> None:
        self._completed.add(self.query_key(q))

    async def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"completed_queries": sorted(self._completed)}
        async with aiofiles.open(self._path, 'w') as f:
            await f.write(json.dumps(data, indent=2))

    async def load(self) -> None:
        if self._path.exists():
            async with aiofiles.open(self._path, 'r') as f:
                data = json.loads(await f.read())
            self._completed = set(data.get("completed_queries", []))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `run_in_executor` for sync-to-async | `asyncio.to_thread` (Python 3.9+) | Python 3.9 | Simpler API; already used in extraction |
| `tenacity.retry` with `wait_exponential` | `wait_exponential_jitter` (tenacity 8.1+) | tenacity 8.1 | Built-in jitter; no need for `wait_random + wait_exponential` combo |
| `pybreaker` for circuit breakers | Hand-roll 30-line CircuitBreaker | N/A | pybreaker adds a dependency; our use case is simple (no half-open timeout complexity) |
| `Retrying` class for async | `AsyncRetrying` / `@retry` with native async support | tenacity 6.0+ | `@retry` auto-detects coroutines; works transparently |

**Deprecated/outdated:**
- `tenacity.retry` with `wait_exponential(multiplier=...)`: Use `wait_exponential_jitter(initial=, max=, jitter=)` instead for built-in jitter.
- `aiofiles` `loop=` parameter: Deprecated since Python 3.10; omit it.

## Integration Analysis

### Where Output Writing Plugs In

The current pipeline flow (based on reading the codebase):

1. `QueryExecutor.run_collection()` returns `list[ArticleRef]`
2. `extract_articles(refs)` returns `list[Article]`
3. `deduplicate_and_filter(articles)` returns `list[Article]`
4. **NEW: Group by state, write JSON + CSV, write metadata**

The output writing happens AFTER all pipeline stages complete. It receives the final `list[Article]` and:
- Groups articles by `article.state`
- Converts state name to slug (need a utility or use the geo_loader)
- Writes per-state JSON and CSV files
- Writes collection-level metadata

### Where Checkpoints Plug In

Checkpoints integrate with `QueryExecutor._execute_query_list()`:

```
Before: for query in queries: result = await scheduler.execute(query)
After:  for query in queries:
            if checkpoint.is_completed(query): continue
            result = await scheduler.execute(query)
            checkpoint.mark_completed(query)
            if batch_complete: await checkpoint.save()
```

**RELI-05 (state before district):** Already implemented by `QueryExecutor.run_collection()` which runs Phase 1 (state) before Phase 2 (district). Checkpoints preserve this ordering naturally.

### Where Circuit Breakers Plug In

Each `SourceScheduler` gets a `CircuitBreaker` instance. Check happens in `SourceScheduler.execute()`:

```
Before: budget check -> language check -> rate limit -> call source
After:  circuit breaker check -> budget check -> language check -> rate limit -> call source
                                                                    -> record_success / record_failure
```

### Where Tenacity Retry Plugs In

The sources' `search()` methods catch all exceptions and return empty lists. To enable retry:

**Recommended approach:** The source `search()` methods must allow HTTP 429 to propagate. Create a `RateLimitError(httpx.HTTPStatusError)` exception. In each source's HTTP error handler, re-raise as `RateLimitError` instead of returning `[]` for 429 status. Tenacity decorator on the HTTP call section catches and retries this.

This preserves the "never raises" contract at the SourceScheduler level (tenacity catches the RateLimitError) while enabling backoff.

### State Slug Mapping for Output

The `Article` model has `state: str` (human-readable name like "Rajasthan"). For directory names, we need slugs. Two options:
1. Use `geo_loader.get_all_regions()` to build a name-to-slug mapping
2. Generate slug from state name (e.g., `state.lower().replace(" ", "-")`)

Option 2 is simpler and sufficient since state names are already consistent in the pipeline.

## Open Questions

1. **Checkpoint save frequency**
   - What we know: "After each completed query batch" (RELI-01). A "batch" could mean each individual query result or each source's complete query list.
   - What's unclear: Individual query vs. batch-of-queries granularity.
   - Recommendation: Save after each individual query completion within `_execute_query_list`. This maximizes recovery granularity. The checkpoint file is small (set of 16-char hex strings), so frequent saves have negligible I/O cost.

2. **Checkpoint file location**
   - What we know: Must persist across pipeline restarts.
   - What's unclear: Should it go in the output directory or a separate location?
   - Recommendation: Store at `output/.checkpoint.json` (hidden file in output root). Delete when a run completes successfully. The date in the output path naturally separates today's checkpoint from yesterday's completed output.

3. **Should CSV exclude full_text?**
   - What we know: OUTP-02 says CSV should "match the JSON structure."
   - What's unclear: `full_text` can be thousands of characters, making CSV unwieldy.
   - Recommendation: Include `full_text` in CSV to match JSON structure per OUTP-02. Users who don't want it can filter columns downstream. High recall principle applies to output too.

4. **Retry integration with existing "never raises" sources**
   - What we know: Sources catch all exceptions. Tenacity needs exceptions to retry.
   - What's unclear: How invasive should the changes to source code be?
   - Recommendation: Introduce a `RateLimitError` exception. Modify the three sources to raise it for HTTP 429 only. The SourceScheduler's tenacity wrapper catches and retries it. All other errors continue to be caught by the source. This is a 5-line change per source.

## Sources

### Primary (HIGH confidence)

- **tenacity 9.0.0 API** -- verified locally via `dir(tenacity)`, `inspect.signature()`, and test execution of `@retry` with `wait_exponential_jitter` on async functions
- **aiofiles 24.1.0 API** -- verified locally via `aiofiles.open()` write/read roundtrip for JSON and CSV
- **Pydantic 2.10.6 `model_dump(mode='json')`** -- verified locally that datetime serializes to ISO string, None is preserved, all types are JSON-serializable
- **csv.DictWriter** -- verified locally with StringIO bridge pattern for special characters (newlines, commas, quotes in article text)
- **Existing codebase** -- all files read directly: `src/models/article.py`, `src/query/_executor.py`, `src/query/_scheduler.py`, `src/query/_models.py`, `src/query/_generator.py`, `src/extraction/_extractor.py`, `src/dedup/__init__.py`, `src/sources/*.py`, `src/output/__init__.py`, `main.py`, `requirements.txt`

### Secondary (MEDIUM confidence)

- **Circuit breaker pattern** -- standard three-state pattern (closed/open/half-open) verified against textbook implementations; no external library needed for simple per-source isolation
- **Checkpoint/resume via JSON** -- common pattern for batch pipeline crash recovery; simpler than SQLite for our use case (set of ~1000 query hashes)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already pinned and verified locally
- Architecture: HIGH -- integration points clearly identified in existing codebase; patterns tested
- Pitfalls: HIGH -- derived from direct codebase analysis (source "never raises" conflict with tenacity, concurrent checkpoint writes, async I/O)

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable domain, pinned library versions)
