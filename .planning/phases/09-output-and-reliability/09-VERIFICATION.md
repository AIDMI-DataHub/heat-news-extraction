---
phase: 09-output-and-reliability
verified: 2026-02-11T10:30:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 9: Output and Reliability Verification Report

**Phase Goal:** The pipeline produces organized JSON/CSV output files and can recover from crashes by resuming from checkpoints

**Verified:** 2026-02-11T10:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline outputs JSON files organized by date and state/UT, with directories created on write | ✓ VERIFIED | `write_json()` creates `output_dir/state_slug` with `mkdir(parents=True, exist_ok=True)` (line 35). Files written to `dest/articles.json`. `write_collection_output()` groups by state slug derived from `article.state`. main.py creates output_dir as `Path("output") / now.strftime("%Y-%m-%d")` (line 64). |
| 2 | Pipeline outputs CSV files organized by date and state/UT, matching the JSON structure | ✓ VERIFIED | `write_csv()` creates identical directory structure (`output_dir/state_slug`, line 67) and includes all fields from `article.model_dump(mode='json')` via DictWriter (lines 76-81). StringIO bridge pattern ensures identical content structure. |
| 3 | Output includes metadata: collection timestamp, sources queried, query terms used, articles found/extracted/filtered counts | ✓ VERIFIED | `CollectionMetadata` frozen model has all 4 required fields (lines 24-27 in _metadata.py). main.py constructs metadata with `collection_timestamp=datetime.now(ist)`, `sources_queried=["google_news", "newsdata", "gnews"]`, `query_terms_used=sorted({ref.search_term for ref in refs})`, and `counts` dict with articles_found/extracted/filtered (lines 124-135). Written as `_metadata.json` via `write_collection_output()` (line 127 in _writers.py). |
| 4 | After each completed query batch, a checkpoint is saved; restarting the pipeline skips already-completed queries | ✓ VERIFIED | `QueryExecutor._execute_query_list()` checks `checkpoint.is_completed(query)` before execution (line 237) and saves checkpoint after EACH query via `await checkpoint.save()` (line 247). main.py loads checkpoint on start (line 101), logs completed count (line 103), and deletes checkpoint only on successful completion (line 145). Checkpoint preserved on failure (line 149). |
| 5 | Each news source has an independent circuit breaker -- if one source fails repeatedly, others continue operating | ✓ VERIFIED | main.py creates 3 independent CircuitBreaker instances (lines 77-79: `google_cb`, `newsdata_cb`, `gnews_cb`), passes each to its corresponding scheduler factory (lines 81-83). SourceScheduler checks `circuit_breaker.is_open` FIRST before budget check (line 171), returns success=True with error="circuit_breaker_open" (line 178), and records success/failure per source (lines 233-234, 246-247). CircuitBreaker state machine (closed/open/half_open) with configurable threshold (default 5 failures) and timeout (default 60s). |
| 6 | Rate limit errors trigger exponential backoff with jitter (via tenacity), not immediate failure | ✓ VERIFIED | All 3 sources re-raise HTTP 429 as `RateLimitError` (google_news.py:207, newsdata.py:201, gnews.py:200). SourceScheduler wraps source call with `@with_rate_limit_retry()` decorator (line 218 in _scheduler.py). `with_rate_limit_retry()` uses `tenacity.wait_exponential_jitter(initial=1, max=60, jitter=5)`, `stop_after_attempt(5)`, `retry_if_exception(is_rate_limit_error)`, and `before_sleep_log` (lines 64-68 in _retry.py). |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/output/_writers.py` | write_json, write_csv, write_collection_output async functions (min 60 lines) | ✓ VERIFIED | EXISTS (141 lines). Contains all 3 functions with aiofiles (4 aiofiles.open calls), ensure_ascii=False (lines 44, 131), mkdir(parents=True, exist_ok=True) (lines 35, 67, 126), Article.model_dump(mode='json') (lines 41, 76, 81), and asyncio.TaskGroup for parallel writes (lines 115-120). |
| `src/output/_metadata.py` | CollectionMetadata frozen Pydantic model (min 20 lines) | ✓ VERIFIED | EXISTS (27 lines). Frozen model with ConfigDict(frozen=True) (line 22) and all 4 required fields: collection_timestamp, sources_queried, query_terms_used, counts (lines 24-27). |
| `src/output/__init__.py` | Re-exports write_json, write_csv, write_collection_output, CollectionMetadata | ✓ VERIFIED | EXISTS (15 lines). Re-exports all 4 symbols with __all__ list (lines 7-14). |
| `src/reliability/_circuit_breaker.py` | CircuitBreaker class with closed/open/half_open state machine (min 40 lines) | ✓ VERIFIED | EXISTS (94 lines). Three-state machine (lines 45, 58, 82, 89). Uses time.monotonic() for timing (lines 57, 87). Configurable failure_threshold (default 5) and reset_timeout (default 60.0). is_open property with auto-recovery (lines 50-65), record_success/record_failure (lines 74-94). |
| `src/reliability/_retry.py` | RateLimitError exception and with_rate_limit_retry tenacity decorator factory (min 25 lines) | ✓ VERIFIED | EXISTS (69 lines). RateLimitError with status_code and source attributes (lines 22-38). with_rate_limit_retry factory returns tenacity.retry with wait_exponential_jitter(initial=1, max=60, jitter=5), stop_after_attempt(max_attempts=5), retry_if_exception(is_rate_limit_error), before_sleep_log, reraise=True (lines 63-69). |
| `src/reliability/_checkpoint.py` | CheckpointStore class with query_key, is_completed, mark_completed, save, load (min 40 lines) | ✓ VERIFIED | EXISTS (96 lines). Static method query_key uses SHA-256 truncated to 16 hex chars (lines 42-52). is_completed checks _completed set (lines 56-58). mark_completed adds to set (lines 60-62). save/load use aiofiles with JSON persistence (lines 66-89). completed_count property (lines 94-96). TYPE_CHECKING guard for Query import (lines 21-22). |
| `src/reliability/__init__.py` | Re-exports CircuitBreaker, RateLimitError, with_rate_limit_retry, CheckpointStore | ✓ VERIFIED | EXISTS (20 lines). Re-exports all 4 reliability symbols with __all__ list. |
| `src/query/_executor.py` | QueryExecutor with CheckpointStore integration for skip/save per query (min 100 lines) | ✓ VERIFIED | EXISTS (267 lines). Optional checkpoint parameter in __init__ (line 55). TYPE_CHECKING import for CheckpointStore (line 33). _execute_query_list checks is_completed before execution (line 237), marks completed and saves after each query (lines 246-247). Logs skipped_checkpoint count (lines 236, 250-254). checkpoint property (lines 66-68). |
| `main.py` | Complete pipeline orchestration wiring all stages end-to-end (min 60 lines) | ✓ VERIFIED | EXISTS (161 lines). Creates 3 sources, 3 circuit breakers, 3 schedulers, 1 generator, 1 executor with checkpoint (lines 73-94). Loads checkpoint on start (line 101). Runs 4 stages sequentially: collection (line 109), extraction (line 114), dedup (line 119), output (line 136). Builds CollectionMetadata with all required fields (lines 124-135). Deletes checkpoint only on success (line 145), preserves on failure (line 149). Closes sources in finally (lines 154-157). API keys from os.environ.get (lines 58-59). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| src/output/_writers.py | src/models/article.py | Article.model_dump(mode='json') for serialization | ✓ WIRED | Pattern found: `a.model_dump(mode="json")` on lines 41, 76, 81 in _writers.py. Import on line 18. |
| src/output/_writers.py | aiofiles | async file I/O for non-blocking writes | ✓ WIRED | Pattern found: `aiofiles.open` on lines 47, 72, 83, 134. Import on line 16. |
| src/output/_writers.py | src/output/_metadata.py | CollectionMetadata import for metadata writing | ✓ WIRED | CollectionMetadata imported on line 19, used in write_collection_output signature (line 92) and model_dump (line 129). |
| src/reliability/_retry.py | tenacity | wait_exponential_jitter and retry_if_exception | ✓ WIRED | tenacity imported on line 17. wait_exponential_jitter used on line 64, retry_if_exception on line 66, stop_after_attempt on line 65, before_sleep_log on line 67. |
| src/query/_scheduler.py | src/reliability/_circuit_breaker.py | CircuitBreaker.is_open check before execution, record_success/record_failure after | ✓ WIRED | TYPE_CHECKING import on line 25. is_open check on line 171, record_success on line 234, record_failure on line 247. Circuit breaker parameter in __init__ (line 145) and all 3 factory functions (lines 295, 310, 328). |
| src/sources/newsdata.py | src/reliability/_retry.py | Re-raise RateLimitError for HTTP 429 instead of returning [] | ✓ WIRED | Inline import on line 199, raise RateLimitError on line 201 for status_code 429. Same pattern in google_news.py (lines 205, 207) and gnews.py (lines 198, 200). |
| src/reliability/_checkpoint.py | aiofiles | Async file I/O for checkpoint persistence | ✓ WIRED | aiofiles imported on line 19. aiofiles.open used in save() (line 70) and load() (line 81). |
| src/query/_executor.py | src/reliability/_checkpoint.py | CheckpointStore.is_completed() and mark_completed() + save() in _execute_query_list | ✓ WIRED | TYPE_CHECKING import on line 33. is_completed called on line 237, mark_completed on line 246, save on line 247, all in _execute_query_list. checkpoint parameter in __init__ (line 55). |
| main.py | src/output/_writers.py | write_collection_output() after dedup+filter stage | ✓ WIRED | Imported on line 33, called on line 136 with filtered articles, output_dir, and metadata. |
| main.py | src/reliability/_circuit_breaker.py | CircuitBreaker instances passed to factory schedulers | ✓ WIRED | CircuitBreaker imported on line 41. Three instances created (lines 77-79), passed to create_google_scheduler (line 81), create_newsdata_scheduler (line 82), create_gnews_scheduler (line 83). |
| main.py | src/query/_executor.py | QueryExecutor.run_collection() returns ArticleRefs | ✓ WIRED | QueryExecutor imported on line 35. Instantiated with checkpoint parameter (lines 86-94). run_collection() called on line 109, result stored in refs. |

### Requirements Coverage

No REQUIREMENTS.md file found mapping requirements to Phase 9, or requirements are tracked elsewhere.

### Anti-Patterns Found

**None detected.** All scanned files passed anti-pattern checks:
- No TODO/FIXME/PLACEHOLDER comments
- No empty implementations (return null/{}[])
- No console.log-only handlers
- All functions have substantive implementations

### Human Verification Required

The following aspects should be manually verified when running the pipeline:

#### 1. JSON/CSV Output Structure and Content

**Test:**
1. Run `python main.py` with valid API keys
2. Navigate to `output/<YYYY-MM-DD>/` directory
3. Verify subdirectories exist for each state (e.g., `delhi/`, `uttar-pradesh/`, `tamil-nadu/`)
4. Open a state directory and verify `articles.json` and `articles.csv` exist
5. Open both files and verify:
   - JSON has state, date, article_count, and articles array
   - CSV has identical fields as JSON articles (including full_text)
   - Indian language scripts (Devanagari, Tamil, etc.) render correctly in both files

**Expected:**
- Directories created per state with kebab-case naming
- Both JSON and CSV present in each state directory
- Content matches between JSON and CSV
- Indian scripts preserved (no Unicode escape sequences like \u0905)

**Why human:** Visual verification of file organization, content structure, and character encoding rendering.

#### 2. Checkpoint Resume After Crash

**Test:**
1. Run `python main.py` and interrupt it mid-execution (Ctrl+C after seeing some query completions logged)
2. Verify `.checkpoint.json` exists in the output directory
3. Re-run `python main.py`
4. Check logs for "Checkpoint loaded: N queries already completed"
5. Verify pipeline skips already-completed queries and continues from where it stopped

**Expected:**
- Checkpoint file persists after crash
- Second run loads checkpoint and skips completed queries
- Second run picks up from interruption point without re-querying

**Why human:** Requires intentional pipeline interruption and observing runtime behavior across multiple runs.

#### 3. Circuit Breaker Opens After Repeated Failures

**Test:**
1. Temporarily break one source (e.g., set invalid NEWSDATA_API_KEY or block network to newsdata.io)
2. Run `python main.py`
3. Watch logs for source failure messages from the broken source
4. After 5 consecutive failures, verify circuit breaker opens (log: "newsdata circuit breaker OPEN after 5 consecutive failures")
5. Verify other sources (google, gnews) continue operating normally
6. Verify queries for broken source return success=True with error="circuit_breaker_open"

**Expected:**
- Circuit breaker opens after configurable threshold (default 5 failures)
- Open circuit prevents further attempts to broken source
- Other sources unaffected by one source's failure
- Pipeline completes successfully using remaining sources

**Why human:** Requires simulating source failures and observing circuit breaker state transitions in logs.

#### 4. Rate Limit Retry with Exponential Backoff

**Test:**
1. Temporarily configure sources to exceed rate limits (e.g., remove rate limiter, increase query volume, or use a restrictive API key)
2. Run `python main.py`
3. Watch logs for HTTP 429 rate limit errors
4. Verify tenacity retry kicks in with exponential backoff (logs: "Retrying... wait X.X seconds")
5. Verify wait times increase: ~1s, ~2s, ~4s, ~8s, up to 60s max
6. Verify jitter (wait times vary slightly due to +/- 5s jitter)
7. After 5 attempts, verify tenacity gives up and circuit breaker records failure

**Expected:**
- HTTP 429 triggers retry, not immediate failure
- Wait times follow exponential pattern with jitter
- After max_attempts (5), exception propagates to circuit breaker
- Circuit breaker opens if rate limits persist across multiple queries

**Why human:** Requires triggering rate limits (difficult to simulate reliably) and observing retry timing in real-time logs.

#### 5. Metadata Accuracy

**Test:**
1. Run `python main.py` end-to-end
2. Open `output/<YYYY-MM-DD>/_metadata.json`
3. Verify all fields present and accurate:
   - `collection_timestamp` matches run time in IST
   - `sources_queried` lists all 3 sources: ["google_news", "newsdata", "gnews"]
   - `query_terms_used` contains heat-related search terms
   - `counts.articles_found` matches total ArticleRefs from Stage 1
   - `counts.articles_extracted` matches articles with non-null full_text from Stage 2
   - `counts.articles_filtered` matches final output count from Stage 3

**Expected:**
- Metadata reflects actual pipeline run
- Counts are consistent across stages
- Timestamp is in IST timezone

**Why human:** Requires running full pipeline and cross-referencing metadata with actual output and stage logs.

---

## Verification Summary

**Status:** PASSED

All 6 success criteria verified:
1. ✓ JSON files organized by date and state with on-demand directory creation
2. ✓ CSV files organized identically to JSON with matching structure
3. ✓ Metadata includes timestamp, sources, query terms, and article counts
4. ✓ Checkpoint saved after each query; pipeline resumes from checkpoint on restart
5. ✓ Independent circuit breakers per source with fail-fast isolation
6. ✓ Rate limit errors trigger exponential backoff with jitter via tenacity

**Artifacts:** All 9 required files exist, meet minimum line counts, and contain substantive implementations (not stubs).

**Wiring:** All 11 key links verified — modules properly import and use each other's functionality.

**Anti-patterns:** None found. No TODOs, placeholders, or empty implementations.

**Phase Goal Achieved:** The pipeline produces organized JSON/CSV output files grouped by date and state, includes collection metadata for traceability, and can recover from crashes by loading checkpoints and skipping already-completed queries. Per-source circuit breakers provide failure isolation, and rate limiting uses exponential backoff with jitter.

**Human Verification:** 5 items flagged for manual testing (output structure, checkpoint resume, circuit breaker behavior, retry backoff, metadata accuracy) — all require runtime observation and cannot be verified programmatically via file inspection.

---

_Verified: 2026-02-11T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
