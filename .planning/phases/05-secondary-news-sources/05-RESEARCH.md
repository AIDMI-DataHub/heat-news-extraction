# Phase 5: Secondary News Sources - Research

**Researched:** 2026-02-10
**Domain:** NewsData.io REST API, GNews REST API, daily quota tracking, async HTTP client reuse, API response mapping to ArticleRef
**Confidence:** HIGH

## Summary

This phase requires building two new source adapters -- `NewsDataSource` and `GNewsSource` -- that implement the existing `NewsSource` Protocol (defined in Phase 4) and return `ArticleRef` objects from their respective REST APIs. Both are straightforward JSON REST APIs authenticated via API key query parameters, queried with `httpx.AsyncClient` (already a dependency), and return JSON responses that map cleanly to `ArticleRef` fields. The primary engineering challenge is not the API integration itself (both are simple GET endpoints) but rather **daily quota management** -- NewsData.io allows 200 requests/day (10 articles each) and GNews allows 100 requests/day (10 articles each on free tier) -- and **graceful degradation** when API keys are missing or quotas are exhausted.

The existing `GoogleNewsSource` in `src/sources/google_news.py` provides an excellent pattern to follow: lazy `httpx.AsyncClient` creation, async context manager for cleanup, never-raise `search()` method, and structured logging. Both new adapters should replicate this structure exactly, substituting RSS parsing with JSON response parsing. No new dependencies are needed -- `httpx` handles HTTP and JSON parsing natively.

A critical finding is that **language support differs significantly across the three APIs**. GNews supports only 6 of our 14 Indian languages (hi, bn, ta, te, mr, ml). NewsData.io claims 89 languages including 13 Indian languages, but the documented language codes in their PHP client only list `hi` -- the remaining Indian language codes need runtime validation. For languages unsupported by a given API, the adapter should silently return empty results rather than making a doomed request.

**Primary recommendation:** Follow the GoogleNewsSource pattern exactly. Use simple in-memory counters for daily quota tracking (this is a daily batch pipeline, not a long-running server). Accept API keys via constructor parameter (loaded from environment variables by the caller). When a key is missing, log a warning at construction time and return empty lists from all `search()` calls without making HTTP requests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async HTTP GET requests to REST APIs, JSON response parsing | Already installed; native async; `response.json()` for parsing |
| pydantic | 2.10.6 | Validate parsed articles into ArticleRef | Already installed; ArticleRef model exists from Phase 2 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os (stdlib) | stdlib | Read API keys from environment variables | `os.environ.get("NEWSDATA_API_KEY")` |
| logging (stdlib) | stdlib | Structured logging for quota warnings, API errors | Every adapter method |
| datetime (stdlib) | stdlib | Parse ISO 8601 date strings from API responses | Converting `pubDate` and `publishedAt` fields |
| zoneinfo (stdlib) | stdlib | UTC/IST timezone handling | Attaching timezone to parsed dates |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw httpx calls | `newsdataapi` Python client | Adds dependency; hides simple GET request behind wrapper; no async support; not needed for one endpoint |
| Raw httpx calls | `gnews` Python library | Wraps Google News RSS, not GNews API; completely different service; would be misleading |
| In-memory quota counter | `pyrate-limiter` with `InMemoryBucket` | Overkill for daily batch pipeline; adds dependency; simple counter is sufficient |
| In-memory quota counter | SQLite/file-based persistence | Unnecessary -- pipeline runs once daily, completes in <45 min; no need to persist across runs |
| Constructor API key | pydantic Settings / python-dotenv | Already not a dependency; caller can use `os.environ.get()` and pass to constructor |

**Installation:**
No additional packages needed. `httpx` is already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  sources/
    __init__.py           # Re-exports: NewsSource, GoogleNewsSource, NewsDataSource, GNewsSource
    _protocol.py          # NewsSource Protocol (existing, unchanged)
    google_news.py        # GoogleNewsSource (existing, unchanged)
    newsdata.py           # NewsDataSource (new)
    gnews.py              # GNewsSource (new)
```

### Pattern 1: Mirror GoogleNewsSource Structure
**What:** Each new adapter follows the exact same class structure as `GoogleNewsSource`: constructor with optional client + timeout, async context manager, `search()` that never raises, lazy client creation via `_ensure_client()`, and `close()` for cleanup.
**When to use:** For both `NewsDataSource` and `GNewsSource`.
**Why:** Consistency makes the codebase predictable. Phase 6 (query engine) can treat all sources identically.
**Example:**
```python
class NewsDataSource:
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout
        self._daily_count = 0
        self._daily_limit = 200
        if not api_key:
            logger.warning("NewsData.io API key not provided; source will return empty results")

    async def __aenter__(self) -> NewsDataSource:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
        *,
        state: str = "",
        search_term: str = "",
    ) -> list[ArticleRef]:
        """Search NewsData.io and return parsed ArticleRefs. Never raises."""
        ...

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client
```

### Pattern 2: In-Memory Daily Quota Counter
**What:** A simple integer counter on the adapter instance, incremented on each successful API call, checked before each request. When the counter reaches the daily limit, `search()` returns an empty list immediately without making an HTTP request.
**When to use:** For both adapters. NewsData.io: 200/day. GNews: 100/day.
**Why:** The pipeline runs once daily and completes within 45 minutes. There is no need for persistent storage, time-window tracking, or external rate limiter libraries. A simple counter is sufficient and correct.
**Example:**
```python
_DAILY_LIMIT = 200  # NewsData.io free tier

async def search(self, query: str, language: str, ...) -> list[ArticleRef]:
    if not self._api_key:
        return []
    if self._daily_count >= self._daily_limit:
        logger.debug("NewsData.io daily limit reached (%d/%d)", self._daily_count, self._daily_limit)
        return []
    # ... make request ...
    self._daily_count += 1
    return articles
```

### Pattern 3: Graceful No-Key Degradation
**What:** When the API key is `None` (not configured), the adapter logs a warning once at construction time and returns empty lists from every `search()` call without making any HTTP requests.
**When to use:** Both adapters. During development and testing, API keys may not be configured.
**Why:** The pipeline must never crash due to missing optional API keys (AUTO-03: zero API budget). Google News is the primary source; these are supplementary.
**Example:**
```python
if not self._api_key:
    return []  # No key configured, skip silently
```

### Pattern 4: JSON Response to ArticleRef Mapping
**What:** Parse the JSON response and map API-specific fields to `ArticleRef` constructor arguments. Skip articles missing required fields (title, url, date).
**When to use:** After receiving HTTP 200 from either API.
**Example for NewsData.io:**
```python
def _article_to_ref(
    article: dict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    title = article.get("title", "")
    link = article.get("link", "")
    pub_date = article.get("pubDate")  # ISO 8601 string
    source_name = article.get("source_name", "") or article.get("source_id", "Unknown")

    if not title or not link or not pub_date:
        return None

    try:
        dt = datetime.fromisoformat(pub_date)  # NewsData.io returns ISO format
    except (ValueError, TypeError):
        return None

    return ArticleRef(
        title=title,
        url=link,
        source=source_name or "Unknown",
        date=dt,
        language=language,
        state=state,
        search_term=search_term,
    )
```

### Anti-Patterns to Avoid
- **Using the `newsdataapi` or `gnews` Python libraries:** These add unnecessary dependencies for what are simple GET requests. The `newsdataapi` library is synchronous. The `gnews` PyPI package wraps Google News RSS, NOT the GNews API at gnews.io.
- **Persisting quota counts to disk/database:** The pipeline runs once daily; in-memory tracking is sufficient and simpler.
- **Making API requests when key is missing:** This wastes time on guaranteed failures. Check key at start of `search()`.
- **Using pagination on free tier:** Each page costs one API credit. With only 200 (NewsData.io) or 100 (GNews) credits/day, pagination should not be used. One request per query, 10 results each, is the correct strategy for free tier.
- **Crashing on API errors:** The Protocol contract says `search()` returns an empty list on failure. Never raise from `search()`.
- **Ignoring language support gaps:** Sending a language code the API does not support may return English results or errors. Check language support before making the request.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON response parsing | Custom string parsing | `response.json()` (httpx built-in) | Handles encoding, content-type validation |
| ISO 8601 date parsing | `strptime` with format strings | `datetime.fromisoformat()` (Python 3.11+) | Handles ISO 8601 natively since Python 3.11 |
| URL query parameter encoding | String concatenation | `httpx` params dict | httpx properly encodes query parameters |
| Daily rate limiting | `pyrate-limiter` / complex token bucket | Simple `self._daily_count` integer | Daily batch pipeline; counter resets naturally per run |
| HTTP retries | Custom retry loop | `tenacity` (already installed) if needed | Already a dependency; but for Phase 5, single-attempt is fine since Phase 9 adds circuit breakers |

**Key insight:** Both APIs return clean JSON with predictable schemas. The mapping to `ArticleRef` is mechanical -- no fuzzy parsing, no XML, no HTML. This is much simpler than the Google News RSS adapter.

## Common Pitfalls

### Pitfall 1: NewsData.io Free Tier Returns 10 Articles Per Request, Not 50
**What goes wrong:** Assuming the free tier returns the same number of articles as paid tiers (50/request). Free tier returns exactly 10 articles per API call.
**Why it happens:** Blog posts and marketing pages mention 50 articles/request without clarifying that is for paid tiers only.
**How to avoid:** Do not set a `size` parameter on free tier. The default (10 articles) is the free tier maximum.
**Warning signs:** Getting fewer articles than expected, or API errors when requesting `size=50`.

### Pitfall 2: NewsData.io Has a 12-Hour Delay on Free Tier
**What goes wrong:** Expecting real-time results from NewsData.io free tier. Results are delayed by approximately 12 hours.
**Why it happens:** Free tier deliberately delays results to differentiate from paid tiers.
**How to avoid:** Accept the delay; for daily batch collection, 12-hour delay is acceptable since we are collecting all recent heat news. Do not use `timeframe` parameter to request very recent articles (last 1-2 hours).
**Warning signs:** Missing articles that appeared in Google News but not in NewsData.io for the same time period.

### Pitfall 3: GNews Free Tier Has 12-Hour Data Freshness Delay
**What goes wrong:** Similar to NewsData.io, GNews free tier articles have a 12-hour delay.
**Why it happens:** Free plan deliberately limits data freshness.
**How to avoid:** Same approach as NewsData.io -- the daily batch pipeline accommodates this delay naturally.

### Pitfall 4: GNews Returns 403 When Daily Quota Exhausted
**What goes wrong:** After 100 requests, every subsequent request returns HTTP 403 (not 429). Confusing 403 with an authentication error could cause the adapter to log misleading error messages.
**Why it happens:** GNews uses 403 for quota exhaustion, reserving 429 for per-second rate limiting (max 1 req/sec on free tier).
**How to avoid:** Detect 403 specifically and check the error message for "reached your request limit". Update the internal quota counter to the limit to prevent further requests.
**Warning signs:** Logs showing "403 Forbidden" after ~100 requests, but the API key is valid.

### Pitfall 5: GNews Per-Second Rate Limit (1 req/sec on Free Tier)
**What goes wrong:** Sending requests too fast triggers HTTP 429 errors.
**Why it happens:** Free tier allows maximum 1 request per second.
**How to avoid:** This is naturally handled by the async pipeline's sequential query processing. If needed, add a 1-second delay between GNews requests. Phase 6 scheduler will manage inter-request timing.
**Warning signs:** HTTP 429 errors from GNews.

### Pitfall 6: Language Support Gaps Across APIs
**What goes wrong:** Sending a language code the API does not support (e.g., `gu` to GNews) and receiving irrelevant English results or errors.
**Why it happens:** Each API supports a different subset of our 14 languages. GNews supports only 6 Indian languages. NewsData.io claims 13 but documentation is inconsistent.
**How to avoid:** Each adapter should have a `_SUPPORTED_LANGUAGES` set. If the requested language is not in the set, return an empty list immediately (log at debug level, not warning, since this is expected for many language/source combos).
**Warning signs:** Getting English articles when searching for Tamil heat terms; unexplained empty results for some languages.

### Pitfall 7: NewsData.io Date Format May Vary
**What goes wrong:** Assuming `pubDate` is always a perfect ISO 8601 string. Some articles may have unusual date formats or `None` values.
**Why it happens:** NewsData.io aggregates from many sources; date normalization is imperfect.
**How to avoid:** Wrap date parsing in try/except. Skip articles with unparseable dates.
**Warning signs:** `ValueError` exceptions when calling `datetime.fromisoformat()`.

### Pitfall 8: Confusing `gnews` PyPI Package with GNews API
**What goes wrong:** Installing the `gnews` Python package from PyPI thinking it wraps the gnews.io API.
**Why it happens:** The `gnews` PyPI package (lowercase) is a wrapper around Google News RSS, completely unrelated to the GNews API at gnews.io.
**How to avoid:** Do NOT install any third-party package. Use raw `httpx` calls to `https://gnews.io/api/v4/search`.
**Warning signs:** Getting Google News RSS results instead of GNews API results; import errors.

## Code Examples

Verified patterns from official API documentation:

### NewsData.io API Call
```python
# Source: https://newsdata.io/documentation
# Endpoint: GET https://newsdata.io/api/1/latest
# Auth: apikey query parameter
# Free tier: 200 credits/day, 10 articles/credit, 30 credits per 15-min window

import httpx

_NEWSDATA_BASE = "https://newsdata.io/api/1/latest"

async def _fetch_newsdata(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    language: str,
    country: str,
) -> dict:
    params = {
        "apikey": api_key,
        "q": query,
        "language": language,
        "country": country,
    }
    response = await client.get(_NEWSDATA_BASE, params=params, timeout=15.0)
    response.raise_for_status()
    return response.json()

# Response format:
# {
#   "status": "success",
#   "totalResults": 10,
#   "results": [
#     {
#       "article_id": "abc123",
#       "title": "Heat wave in Rajasthan claims 12 lives",
#       "link": "https://example.com/article/123",
#       "description": "Brief summary...",
#       "content": null,  # null on free tier (full_content not available)
#       "pubDate": "2026-02-10 08:30:00",
#       "image_url": "https://...",
#       "source_id": "times_of_india",
#       "source_name": "Times of India",
#       "source_url": "https://timesofindia.indiatimes.com",
#       "source_icon": "https://...",
#       "source_priority": 1234,
#       "country": ["india"],
#       "category": ["environment"],
#       "language": "en",
#       "ai_tag": "heat wave",
#       "ai_region": "Rajasthan, India",
#       "sentiment": "negative",
#       "sentiment_stats": { ... },
#       "keywords": ["heat wave", "rajasthan"],
#       "creator": ["Author Name"],
#       "video_url": null,
#       "duplicate": false
#     }
#   ],
#   "nextPage": "1707123456789"  # pagination token (each page = 1 credit)
# }
```

### GNews API Call
```python
# Source: https://docs.gnews.io/endpoints/search-endpoint
# Endpoint: GET https://gnews.io/api/v4/search
# Auth: apikey query parameter (or X-Api-Key header)
# Free tier: 100 requests/day, max 10 articles/request, 1 req/sec

import httpx

_GNEWS_BASE = "https://gnews.io/api/v4/search"

async def _fetch_gnews(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    language: str,
    country: str,
) -> dict:
    params = {
        "apikey": api_key,
        "q": query,
        "lang": language,   # Note: "lang" not "language"
        "country": country.lower(),  # GNews uses lowercase country codes
        "max": 10,
    }
    response = await client.get(_GNEWS_BASE, params=params, timeout=15.0)
    response.raise_for_status()
    return response.json()

# Response format:
# {
#   "totalArticles": 245,
#   "articles": [
#     {
#       "id": "unique-id-string",
#       "title": "Heat wave in Rajasthan claims 12 lives",
#       "description": "Brief summary...",
#       "content": "Truncated on free tier...",
#       "url": "https://example.com/article/123",
#       "image": "https://...",
#       "publishedAt": "2026-02-10T08:30:00Z",  # ISO 8601, always UTC
#       "lang": "en",
#       "source": {
#         "id": "times-of-india",
#         "name": "Times of India",
#         "url": "https://timesofindia.indiatimes.com",
#         "country": "in"
#       }
#     }
#   ]
# }
```

### NewsData.io Response to ArticleRef Mapping
```python
# Source: NewsData.io response format + existing ArticleRef model
from datetime import datetime, timezone

def _newsdata_to_ref(
    article: dict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    title = (article.get("title") or "").strip()
    link = (article.get("link") or "").strip()
    pub_date_str = article.get("pubDate")
    source_name = article.get("source_name") or article.get("source_id") or "Unknown"

    if not title or not link or not pub_date_str:
        return None

    # NewsData.io pubDate format: "2026-02-10 08:30:00" (space-separated, no T)
    # Python's fromisoformat handles this since 3.11
    try:
        dt = datetime.fromisoformat(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)  # Assume UTC if no tz
    except (ValueError, TypeError):
        return None

    try:
        return ArticleRef(
            title=title,
            url=link,
            source=source_name,
            date=dt,
            language=language,
            state=state,
            search_term=search_term,
        )
    except Exception:
        return None
```

### GNews Response to ArticleRef Mapping
```python
# Source: GNews response format + existing ArticleRef model
from datetime import datetime, timezone

def _gnews_to_ref(
    article: dict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    title = (article.get("title") or "").strip()
    url = (article.get("url") or "").strip()
    published_at = article.get("publishedAt")
    source = article.get("source", {})
    source_name = source.get("name", "Unknown")

    if not title or not url or not published_at:
        return None

    # GNews publishedAt format: "2026-02-10T08:30:00Z" (ISO 8601, always UTC)
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None

    try:
        return ArticleRef(
            title=title,
            url=url,
            source=source_name,
            date=dt,
            language=language,
            state=state,
            search_term=search_term,
        )
    except Exception:
        return None
```

### Error Handling for Both APIs
```python
# Verified error response formats:

# NewsData.io error response:
# HTTP 200 with {"status": "error", "results": {"message": "...", "code": "..."}}
# OR standard HTTP 4xx/5xx

# GNews error responses (from https://docs.gnews.io/error-handling):
# HTTP 400: {"errors": ["Invalid parameter ..."]}
# HTTP 401: {"errors": ["Your API key is invalid."]}
# HTTP 403: {"errors": ["You have reached your request limit for today..."]}
# HTTP 429: {"errors": ["Too many requests..."]}  (per-second limit)
# HTTP 500: {"errors": ["Internal server error"]}

async def search(self, ...) -> list[ArticleRef]:
    try:
        response = await client.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 403:
            # Likely quota exhausted -- stop further requests this run
            self._daily_count = self._daily_limit
            logger.warning("API quota exhausted (HTTP 403)")
        elif status == 429:
            logger.warning("Rate limited (HTTP 429)")
        elif status == 401:
            logger.error("Invalid API key (HTTP 401)")
        else:
            logger.warning("HTTP %d error", status)
        return []
    except httpx.TimeoutException:
        logger.warning("Request timed out")
        return []
    except httpx.RequestError as exc:
        logger.warning("Network error: %s", exc)
        return []
```

## API Comparison Matrix

| Feature | NewsData.io | GNews |
|---------|------------|-------|
| **Endpoint** | `https://newsdata.io/api/1/latest` | `https://gnews.io/api/v4/search` |
| **Auth** | `apikey` query param | `apikey` query param or `X-Api-Key` header |
| **Query param** | `q` | `q` |
| **Language param** | `language` | `lang` |
| **Country param** | `country` | `country` |
| **Free daily limit** | 200 requests | 100 requests |
| **Results/request** | 10 (free), 50 (paid) | 10 (free), up to 100 (paid) |
| **Data freshness** | 12-hour delay (free) | 12-hour delay (free) |
| **Search char limit** | 100 chars (free) | 200 chars |
| **Date format** | `"2026-02-10 08:30:00"` (space, no T) | `"2026-02-10T08:30:00Z"` (ISO 8601) |
| **Quota exhausted** | Undocumented (likely 4xx) | HTTP 403 |
| **Rate limit** | 30 req / 15 min | 1 req / sec |
| **Per-sec limit hit** | Undocumented | HTTP 429 |
| **Error format** | `{"status": "error", ...}` | `{"errors": [...]}` |
| **Article URL field** | `link` | `url` |
| **Source name field** | `source_name` | `source.name` |
| **Date field** | `pubDate` | `publishedAt` |

## Language Support Matrix

### GNews Supported Indian Languages (from official docs)
| Our Code | GNews `lang` | Language | Confidence |
|----------|-------------|----------|------------|
| hi | hi | Hindi | HIGH - listed in official docs |
| bn | bn | Bengali | HIGH - listed in official docs |
| ta | ta | Tamil | HIGH - listed in official docs |
| te | te | Telugu | HIGH - listed in official docs |
| mr | mr | Marathi | HIGH - listed in official docs |
| ml | ml | Malayalam | HIGH - listed in official docs |
| pa | pa | Punjabi | MEDIUM - listed in GNews docs search endpoint |
| en | en | English | HIGH - listed in official docs |
| gu | -- | Gujarati | NOT SUPPORTED by GNews |
| kn | -- | Kannada | NOT SUPPORTED by GNews |
| or | -- | Odia | NOT SUPPORTED by GNews |
| as | -- | Assamese | NOT SUPPORTED by GNews |
| ur | -- | Urdu | NOT SUPPORTED by GNews |
| ne | -- | Nepali | NOT SUPPORTED by GNews |

**Source:** GNews search endpoint docs list `lang` values: ar, bn, zh, nl, en, fr, de, el, he, hi, id, it, ja, ml, mr, no, pt, pa, ro, ru, es, sv, ta, te, tr, uk. This is 26 languages. Notably missing: gu, kn, or, as, ur, ne.

### NewsData.io Supported Indian Languages
| Our Code | NewsData `language` | Language | Confidence |
|----------|-------------------|----------|------------|
| hi | hi | Hindi | HIGH - confirmed in PHP client docs |
| en | en | English | HIGH - confirmed in PHP client docs |
| bn | bn | Bengali | MEDIUM - claimed on India page; not in PHP client |
| ta | ta | Tamil | MEDIUM - claimed on India page; not in PHP client |
| te | te | Telugu | MEDIUM - claimed on India page; not in PHP client |
| mr | mr | Marathi | MEDIUM - claimed on India page; not in PHP client |
| gu | gu | Gujarati | MEDIUM - claimed on India page; not in PHP client |
| kn | kn | Kannada | LOW - claimed "13 Indian languages" but not named |
| ml | ml | Malayalam | MEDIUM - claimed on India page; not in PHP client |
| pa | pa | Punjabi | MEDIUM - claimed on India page; not in PHP client |
| ur | ur | Urdu | MEDIUM - claimed on India page; not in PHP client |
| as | as | Assamese | LOW - claimed "13 Indian languages" but not named |
| or | or | Odia | LOW - not explicitly confirmed anywhere |
| ne | ne | Nepali | LOW - not explicitly confirmed anywhere |

**Source:** The PHP client README lists only 34 language codes (primarily European + hi). But marketing pages claim 89 languages including "13 Indian languages: Assamese, Bengali, Gujarati, Marathi, Hindi, Tamil, Telugu, Punjabi, Urdu, etc." The Python client does not validate language codes client-side. The discrepancy suggests the PHP client list is outdated and the API likely accepts standard ISO 639-1 codes for supported Indian languages.

**Recommendation:** Include all 14 language codes in the `_SUPPORTED_LANGUAGES` set for NewsData.io. The API will simply return no results for unsupported languages rather than erroring. For GNews, restrict to the 8 confirmed languages (en, hi, bn, ta, te, mr, ml, pa).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| newsdata.io Python client (sync) | Direct httpx.AsyncClient calls | 2024+ | Async, no extra dependency, full control |
| gnews PyPI package (Google News wrapper) | Direct httpx calls to gnews.io API | N/A | gnews PyPI wraps Google News RSS, not GNews API -- different service entirely |
| File-based quota persistence | In-memory counter per run | N/A | Pipeline runs once daily; persistence unnecessary |
| Environment variable lookup at module level | Constructor parameter with env var lookup by caller | 2024+ | Testable, explicit, no hidden global state |

**Deprecated/outdated:**
- `gnews` PyPI package: Wraps Google News RSS, NOT the GNews API at gnews.io. Do not use.
- `newsdataapi` Python library: Adds synchronous dependency for what is a single GET request. Not needed.

## Open Questions

1. **What are the exact ISO 639-1 language codes NewsData.io accepts for Indian languages?**
   - What we know: Marketing says "13 Indian languages" including Assamese, Bengali, Gujarati, Marathi, Hindi, Tamil, Telugu, Punjabi, Urdu. PHP client README only lists `hi`. Python client does not validate.
   - What's unclear: Whether codes like `ta`, `te`, `bn`, `kn`, `ml` are accepted by the API.
   - Recommendation: Use standard ISO 639-1 codes. The API likely accepts them since the Python client passes them through without validation. Validate at implementation time by making test requests. LOW-confidence languages (as, or, ne, kn) should be tested specifically.

2. **What HTTP status does NewsData.io return when daily quota is exhausted?**
   - What we know: Documentation only says "Rate Limit Exceeded" message appears. The rate limit blog mentions "the API will show 'Rate Limit Exceeded'" but no HTTP code.
   - What's unclear: Whether it returns 429, 403, or HTTP 200 with `{"status": "error"}`.
   - Recommendation: Handle all three cases. Check response JSON for `"status": "error"` even on HTTP 200. On any 4xx, inspect the error message. When quota is detected as exhausted, set `_daily_count = _daily_limit` to prevent further requests.

3. **Does each NewsData.io pagination request consume an API credit?**
   - What we know: Documentation implies "pagination continues until credits are exhausted". Each page returns 10 articles and likely costs 1 credit.
   - What's unclear: Whether the nextPage request is "free" or costs a credit.
   - Recommendation: Do NOT use pagination. Each `search()` call makes exactly one request, gets up to 10 articles, and returns them. With 200 credits/day, pagination would cut the number of unique queries in half or worse. Each credit should go to a different query to maximize coverage.

4. **Does NewsData.io `pubDate` always include timezone information?**
   - What we know: Example responses show format like `"2026-02-10 08:30:00"` with no timezone.
   - What's unclear: Whether some articles include timezone offsets.
   - Recommendation: Use `datetime.fromisoformat()` which handles both. If no timezone, assume UTC (consistent with how Google News RSS dates are handled). The ArticleRef validator will convert to IST.

5. **Is GNews `pa` (Punjabi) actually supported on free tier?**
   - What we know: The search endpoint docs list `pa` in the `lang` parameter values.
   - What's unclear: Whether free tier restrictions apply to language availability.
   - Recommendation: Include `pa` in supported languages. If it returns errors or empty results at runtime, the adapter handles it gracefully.

## Sources

### Primary (HIGH confidence)
- [GNews Search Endpoint docs](https://docs.gnews.io/endpoints/search-endpoint) - Complete parameter list, response format, supported languages
- [GNews Error Handling docs](https://docs.gnews.io/error-handling) - HTTP status codes 200/400/401/403/429/500/503, error JSON format
- [GNews JSON Response docs](https://docs.gnews.io/json-response) - Complete article and source object fields
- [GNews Authentication docs](https://docs.gnews.io/authentication) - Query param `apikey` or `X-Api-Key` header
- [GNews Pricing](https://gnews.io/pricing) - Free: 100 req/day, 10 articles/req, 30-day history, 12hr delay, 1 req/sec
- Existing codebase: `src/sources/google_news.py` - Pattern to follow for adapter structure
- Existing codebase: `src/sources/_protocol.py` - Protocol interface that new adapters must satisfy
- Existing codebase: `src/models/article.py` - ArticleRef model fields and validators

### Secondary (MEDIUM confidence)
- [NewsData.io Latest News Endpoint blog](https://newsdata.io/blog/latest-news-endpoint/) - All query parameters documented
- [NewsData.io Response Objects blog](https://newsdata.io/blog/news-api-response-object/) - Response fields: article_id, title, link, pubDate, source_name, source_id, country, language, etc.
- [NewsData.io Rate Limit blog](https://newsdata.io/blog/newsdata-rate-limit/) - Free: 200 credits/day, 30 per 15 min, 10 articles/credit
- [NewsData.io Pricing blog](https://newsdata.io/blog/pricing-plan-in-newsdata-io/) - Free: 200 credits/day, 12hr delay, no full content, 100-char search limit
- [NewsData.io India blog](https://newsdata.io/blog/news-api-for-india/) - Claims 13 Indian languages supported
- [NewsData.io PHP client README](https://github.com/bytesview/php-client) - Language codes list (only `hi` for Indian), country codes list (includes `in`)
- [NewsData.io Python client constants](https://github.com/newsdataapi/python-client) - Base URL: `https://newsdata.io/api/1/`, endpoints: `latest`, `archive`, `sources`
- [Carlos Toruno blog](https://www.carlos-toruno.com/blog/classification-system/01-gathering-data/) - Practical NewsData.io usage confirming response structure

### Tertiary (LOW confidence)
- NewsData.io Indian language codes beyond `hi` - claimed on marketing pages but not confirmed in client libraries or API documentation
- NewsData.io error HTTP status codes - not documented explicitly; inferred from general API patterns
- NewsData.io `pubDate` timezone behavior - not documented; assumed UTC based on common API patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - httpx already installed; JSON REST APIs are simple; no new dependencies needed
- Architecture: HIGH - Follows established GoogleNewsSource pattern exactly; Protocol already defined
- GNews API details: HIGH - Official documentation is thorough and current (endpoint, params, response, errors, languages)
- NewsData.io API details: MEDIUM - Blog-based documentation is scattered; language support claims vs. client libraries disagree; error handling underdocumented
- Language support mapping: MEDIUM for confirmed languages (GNews: hi, bn, ta, te, mr, ml); LOW for unconfirmed (NewsData.io Indian languages beyond hi; GNews: pa)
- Pitfalls: HIGH - Identified from official docs (GNews 403 on quota, 429 on rate), free tier restrictions confirmed

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days -- REST API endpoints and free tier limits are stable)
