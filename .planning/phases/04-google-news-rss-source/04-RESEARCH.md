# Phase 4: Google News RSS Source - Research

**Researched:** 2026-02-10
**Domain:** Google News RSS feed parsing, async HTTP, common source interface design, feedparser integration
**Confidence:** HIGH

## Summary

This phase requires building a `GoogleNewsSource` class that implements a common source interface (`search(query, language, country) -> List[ArticleRef]`) and fetches/parses Google News RSS feeds. The core technical challenges are: (1) constructing correct Google News RSS search URLs with language/country parameters for 14 Indian languages, (2) bridging sync feedparser with async httpx, (3) parsing RSS entry fields into the existing `ArticleRef` Pydantic model, and (4) handling Google News's undocumented rate limits and redirect URLs gracefully.

The existing monsoon pipeline at `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/` provides a production-tested reference implementation using `pygooglenews` (a wrapper around Google News RSS + feedparser). However, the heat pipeline should NOT use `pygooglenews` -- it is unmaintained (last updated 2021), uses synchronous `requests`, and adds unnecessary abstraction. Instead, use `httpx` (already a dependency, async-capable) to fetch the raw RSS XML, then `feedparser.parse()` on the response text. This is the approach recommended by feedparser's maintainer for async codebases.

The common source interface should use `typing.Protocol` (structural subtyping) rather than `abc.ABC` (nominal subtyping). Protocol requires no inheritance, works with static type checkers, and is the modern Python approach for interface contracts. Phase 5 sources (NewsData.io, GNews) will implement the same Protocol without needing to subclass anything.

**Primary recommendation:** Use `httpx.AsyncClient` to fetch RSS XML, `feedparser.parse(response.text)` to parse entries, and `typing.Protocol` for the common source interface. Do NOT add `googlenewsdecoder` or `pygooglenews` as dependencies -- Google News redirect URLs can be followed via httpx during the Article extraction phase (Phase 7), not during search.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async HTTP client to fetch RSS XML | Already installed; async-native; supports timeouts, retries |
| feedparser | 6.0.11 | Parse RSS XML into structured entries | Already installed; de facto standard for RSS; handles edge cases |
| pydantic | 2.10.6 | Validate parsed entries into ArticleRef | Already installed; ArticleRef model exists from Phase 2 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing (stdlib) | stdlib | Protocol class for common source interface | Defining the NewsSource protocol |
| urllib.parse (stdlib) | stdlib | URL encoding of search queries | Encoding non-Latin search terms in RSS URLs |
| datetime (stdlib) | stdlib | Converting feedparser time tuples to datetime | Parsing `published_parsed` from RSS entries |
| zoneinfo (stdlib) | stdlib | UTC/IST timezone handling | Attaching timezone to parsed dates |
| asyncio (stdlib) | stdlib | `loop.run_in_executor` for feedparser bridge | Running sync feedparser.parse() in async context |
| logging (stdlib) | stdlib | Structured logging for debug/error tracking | Rate limit warnings, parse failures, empty results |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw httpx + feedparser | pygooglenews | pygooglenews is unmaintained (2021), synchronous, adds unnecessary wrapper; raw approach gives full control |
| Raw httpx + feedparser | google-news-feed (aiohttp+lxml) | Adds aiohttp dependency conflicting with httpx; lxml is heavy; project already has httpx |
| typing.Protocol | abc.ABC | ABC requires subclassing; Protocol uses structural subtyping (duck typing); Protocol is more Pythonic for this use case |
| googlenewsdecoder for URL resolution | httpx redirect following | URL resolution is Phase 7 concern (article extraction); during search phase, the Google News URL is sufficient as the ArticleRef.url |

**Installation:**
No additional packages needed. All requirements are already satisfied by Phase 1's `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  sources/
    __init__.py           # Re-exports NewsSource protocol + GoogleNewsSource
    _protocol.py          # NewsSource Protocol definition
    google_news.py        # GoogleNewsSource implementation
```

### Pattern 1: typing.Protocol for Common Source Interface
**What:** Define a `NewsSource` Protocol class that specifies the `search()` method signature. Any class with a matching `search()` method satisfies the protocol without inheritance.
**When to use:** For the common interface that GoogleNewsSource, NewsDataSource, and GNewsSource will all implement.
**Example:**
```python
# Source: https://typing.python.org/en/latest/spec/protocol.html
from typing import Protocol, runtime_checkable
from src.models.article import ArticleRef

@runtime_checkable
class NewsSource(Protocol):
    """Common interface for all news source adapters."""

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
    ) -> list[ArticleRef]:
        """Search for articles matching the query.

        Args:
            query: Search terms (may contain non-Latin scripts).
            language: ISO 639-1 language code (e.g., 'hi', 'ta').
            country: ISO 3166-1 alpha-2 country code (default: 'IN').

        Returns:
            List of ArticleRef objects parsed from search results.
        """
        ...
```

### Pattern 2: Async HTTP Fetch + Sync Feedparser Parse
**What:** Use `httpx.AsyncClient.get()` to fetch the RSS XML asynchronously, then pass the response text to `feedparser.parse()` (which is synchronous but CPU-bound, not I/O-bound, so it completes quickly on RSS-sized payloads). No need for `run_in_executor` -- feedparser parsing of a single RSS feed (100 entries max) is near-instantaneous.
**When to use:** Every time GoogleNewsSource.search() is called.
**Example:**
```python
import feedparser
import httpx

async def _fetch_and_parse(client: httpx.AsyncClient, url: str) -> feedparser.FeedParserDict:
    """Fetch RSS feed and parse it."""
    response = await client.get(url, timeout=15.0)
    response.raise_for_status()
    # feedparser.parse() on a string is pure parsing, no I/O
    return feedparser.parse(response.text)
```

### Pattern 3: Google News RSS URL Construction
**What:** Build the search URL from query, language, and country parameters using the documented URL format.
**When to use:** Inside GoogleNewsSource to construct the RSS feed URL for each search call.
**Example:**
```python
from urllib.parse import quote_plus

def _build_search_url(query: str, language: str, country: str) -> str:
    """Build Google News RSS search URL.

    URL format: https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang}
    """
    encoded_query = quote_plus(query)
    return (
        f"https://news.google.com/rss/search"
        f"?q={encoded_query}"
        f"&hl={language}"
        f"&gl={country}"
        f"&ceid={country}:{language}"
    )
```

### Pattern 4: RSS Entry to ArticleRef Conversion
**What:** Map feedparser entry fields to ArticleRef constructor arguments, handling missing fields and date parsing.
**When to use:** After feedparser returns parsed entries, convert each to an ArticleRef.
**Example:**
```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def _entry_to_article_ref(
    entry: feedparser.FeedParserDict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    """Convert a feedparser entry to an ArticleRef, or None if unparseable."""
    title = getattr(entry, "title", None)
    link = getattr(entry, "link", None)
    if not title or not link:
        return None

    # Source name: entry.source.title if present, else extract from title
    source_name = ""
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        source_name = entry.source.title
    elif " - " in title:
        # Google News often appends " - Source Name" to titles
        source_name = title.rsplit(" - ", 1)[-1]

    # Date parsing: published_parsed is a time.struct_time in UTC
    pub_date = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

    if pub_date is None:
        return None  # Skip entries without dates

    return ArticleRef(
        title=title,
        url=link,
        source=source_name or "Unknown",
        date=pub_date,  # ArticleRef's validator will convert to IST
        language=language,
        state=state,
        search_term=search_term,
    )
```

### Anti-Patterns to Avoid
- **Using pygooglenews:** Unmaintained since 2021, synchronous, adds an unnecessary dependency layer. Build directly on httpx + feedparser.
- **Resolving Google News redirect URLs at search time:** This is expensive (requires an HTTP request per article) and belongs in Phase 7 (article extraction). Store the Google News URL as-is in ArticleRef.url.
- **Adding googlenewsdecoder as a dependency:** The decode logic requires making HTTP requests to Google servers (batchexecute endpoint), which adds rate limit risk. Defer URL resolution to Phase 7.
- **Using `run_in_executor` for feedparser:** feedparser.parse() on a string (not a URL) is pure CPU parsing, not I/O. For RSS-sized payloads (typically < 100KB), it completes in milliseconds. No executor needed.
- **Blocking on missing entry fields:** Google News RSS entries occasionally lack `source` or have malformed dates. Skip individual entries gracefully, do not fail the entire search.
- **Hardcoding `when` parameter in the URL:** The `when` parameter (`when:7d`, `when:1d`) should not be hardcoded into the GoogleNewsSource. It can be appended to the query string by the caller (Phase 6 query engine) if needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS XML parsing | Custom XML parser with ElementTree | `feedparser.parse(response.text)` | feedparser handles RSS 0.9x, 1.0, 2.0, Atom, CDF; normalizes field names; handles encoding edge cases |
| Date parsing from RSS | `datetime.strptime` with format guessing | `feedparser.published_parsed` -> `datetime(*t[:6])` | feedparser already parses RFC 822 dates into time tuples; just convert to datetime |
| URL encoding for non-Latin queries | Manual percent-encoding | `urllib.parse.quote_plus()` | Handles all Unicode correctly, including Devanagari, Tamil, etc. |
| Rate limiting / circuit breaker | Custom implementation (like monsoon's SmartGoogleNewsHandler) | `tenacity` (already installed) for retries; simple delay between requests | tenacity handles exponential backoff with jitter; circuit breaker is Phase 9 scope |
| HTTP request retries | Custom retry loop | `tenacity.retry` decorator or httpx's built-in retry | tenacity is already a dependency; provides configurable retry with backoff |
| Common source interface | abc.ABC with @abstractmethod | `typing.Protocol` with `@runtime_checkable` | Protocol works with duck typing; no inheritance required; cleaner for static analysis |

**Key insight:** The monsoon pipeline's `SmartGoogleNewsHandler` (400+ lines of rate limiting, circuit breaker, session management, user agent rotation) is massively over-engineered for this phase. The heat pipeline already has `tenacity` for retries and will add circuit breakers in Phase 9. Phase 4 should be a thin adapter: fetch RSS, parse entries, return ArticleRefs.

## Common Pitfalls

### Pitfall 1: Google News RSS Returns Max 100 Results Per Query
**What goes wrong:** Assuming pagination exists or that more than 100 results can be fetched per query. There is no pagination mechanism for Google News RSS -- each request returns at most ~100 entries.
**Why it happens:** Google News RSS is undocumented; there is no `start` or `page` parameter.
**How to avoid:** Accept the 100-result limit per query. Design the query engine (Phase 6) to use multiple specific queries (term + location combinations) rather than relying on one broad query returning everything.
**Warning signs:** Expecting more than 100 results from a single search() call.

### Pitfall 2: Language Code Format Varies Between Google News and Our Models
**What goes wrong:** Google News uses `hl=hi` (simple code) for most Indian languages but uses `hl=en-IN` (with country suffix) for English in India. Our ArticleRef model uses bare codes (`en`, `hi`, `ta`).
**Why it happens:** Google's hl parameter format is inconsistent -- some languages use bare codes, English often uses regional variants.
**How to avoid:** Map our 14 language codes to Google News hl codes. For most Indian languages, they match directly (`hi` -> `hi`, `ta` -> `ta`). For English in India, use `en-IN`. Build a mapping dict inside GoogleNewsSource.
**Warning signs:** Getting English-US results instead of English-India results when searching with `hl=en`.

### Pitfall 3: Google News RSS Entry Source Field Is Sometimes Missing
**What goes wrong:** Expecting `entry.source.title` to always exist. Some Google News entries do not have a `<source>` element in the RSS, which means feedparser will not set the `source` attribute.
**Why it happens:** Not all RSS entries from Google News include the `<source>` tag, particularly for aggregated or syndicated stories.
**How to avoid:** Check `hasattr(entry, 'source')` before accessing. Fall back to extracting source from the title string (Google News appends " - Source Name" to titles).
**Warning signs:** `AttributeError: 'FeedParserDict' object has no attribute 'source'` during parsing.

### Pitfall 4: Google News Redirect URLs vs Actual Article URLs
**What goes wrong:** Google News RSS entries contain URLs like `https://news.google.com/rss/articles/CBMi...` which are redirect/encoded URLs, not the actual article URLs. Trying to extract article text from these URLs in later phases will fail.
**Why it happens:** Google News wraps all article URLs in its own redirect/tracking layer since ~2023. New-style URLs (starting with `AU_yqL`) require server-side decoding via Google's `batchexecute` endpoint.
**How to avoid:** For Phase 4, store the Google News URL as-is in ArticleRef.url (the prior decision [02-01] chose `str` type for url specifically to handle unusual URL schemes). URL resolution is a Phase 7 concern. Do NOT try to decode URLs at search time.
**Warning signs:** Adding googlenewsdecoder dependency or making extra HTTP requests per article during search.

### Pitfall 5: Rate Limiting from GitHub Actions IPs
**What goes wrong:** Google News returns 429 (Too Many Requests) or empty results when too many requests come from GitHub Actions runners (shared IP pool).
**Why it happens:** GitHub Actions runners share IP addresses across many users. Google may rate-limit based on IP.
**How to avoid:** Build delay capability into GoogleNewsSource (configurable delay between requests, defaulting to a conservative value like 1-2 seconds). The Phase 6 scheduler will manage actual timing. For Phase 4, expose the delay as a constructor parameter. Use `tenacity` retry with exponential backoff for transient failures.
**Warning signs:** Tests passing locally but failing in CI; 429 responses; empty result sets for queries that should return results.

### Pitfall 6: Feedparser published_parsed Returns UTC, Not IST
**What goes wrong:** Treating feedparser's `published_parsed` time tuple as IST when it is actually UTC/GMT. All Google News RSS dates are in GMT (format: `Sat, 08 Feb 2025 12:00:00 GMT`).
**Why it happens:** Google News RSS uses RFC 822 dates with GMT timezone. Feedparser normalizes these to UTC in the `published_parsed` tuple.
**How to avoid:** Always construct datetime with `tzinfo=timezone.utc` from `published_parsed`, then let the ArticleRef's `field_validator` convert to IST via `astimezone()`.
**Warning signs:** All articles appearing 5.5 hours off from expected times.

### Pitfall 7: Non-Latin Query Terms Need Proper URL Encoding
**What goes wrong:** Hindi/Tamil/Telugu search terms are corrupted in the URL, returning no results or wrong results.
**Why it happens:** Non-ASCII characters must be properly percent-encoded in the URL query parameter.
**How to avoid:** Use `urllib.parse.quote_plus()` which correctly handles all Unicode. Do NOT manually encode or use `str.encode('utf-8')`.
**Warning signs:** Empty results when searching in non-English languages despite identical terms working on news.google.com in a browser.

## Code Examples

Verified patterns from research:

### Complete GoogleNewsSource Class Skeleton
```python
"""Google News RSS source adapter."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from src.models.article import ArticleRef

logger = logging.getLogger(__name__)

# Google News RSS base URL
_BASE_URL = "https://news.google.com/rss/search"

# Map our language codes to Google News hl parameter
_LANG_TO_HL: dict[str, str] = {
    "en": "en-IN",  # English for India specifically
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "or": "or",     # Odia -- verify Google News supports this
    "pa": "pa",
    "as": "as",     # Assamese -- verify Google News supports this
    "ur": "ur",
    "ne": "ne",     # Nepali -- verify Google News supports this
}


class GoogleNewsSource:
    """Fetches and parses Google News RSS search results."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
    ) -> list[ArticleRef]:
        """Search Google News RSS and return parsed ArticleRefs."""
        # Implementation here
        ...

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
```

### Feedparser Entry Field Access Pattern
```python
# Source: feedparser 6.0.11 docs + Google News RSS structure
# https://feedparser.readthedocs.io/en/latest/common-rss-elements/

# Google News RSS entry fields available via feedparser:
entry.title              # str: "Heat wave kills 12 in Rajasthan - Times of India"
entry.link               # str: "https://news.google.com/rss/articles/CBMi..."
entry.published          # str: "Sat, 08 Feb 2025 12:00:00 GMT" (RFC 822)
entry.published_parsed   # time.struct_time: (2025, 2, 8, 12, 0, 0, 5, 39, 0) -- UTC
entry.summary            # str: HTML snippet of article description
entry.source             # FeedParserDict (may not exist): .title = "Times of India"
entry.id                 # str: GUID of the entry
```

### Date Conversion: feedparser time tuple to IST-aware datetime
```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def _parse_pub_date(entry) -> datetime | None:
    """Parse feedparser entry's publication date to IST-aware datetime."""
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        return None
    t = entry.published_parsed
    # feedparser normalizes all dates to UTC in published_parsed
    utc_dt = datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=timezone.utc)
    return utc_dt  # ArticleRef's field_validator will convert to IST
```

### Source Name Extraction with Fallback
```python
def _extract_source_name(entry) -> str:
    """Extract publisher name from RSS entry with fallback strategies."""
    # Strategy 1: entry.source.title (if <source> element exists)
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        return entry.source.title

    # Strategy 2: Google News appends " - Source Name" to titles
    title = getattr(entry, "title", "")
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()

    return "Unknown"
```

### Google News RSS URL Format Reference
```python
# Search URL format (all parameters documented via reverse engineering):
# https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang}
#
# Parameters:
#   q      = URL-encoded search query
#            Supports: "term" (exact match), OR, intitle:, when:7d, after:YYYY-MM-DD, before:YYYY-MM-DD
#   hl     = Interface language (hi, ta, te, bn, mr, gu, kn, ml, en-IN, etc.)
#   gl     = Country code (IN for India)
#   ceid   = Country:Language combo (IN:hi, IN:ta, IN:en)
#
# Response:
#   - RSS 2.0 XML
#   - Max 100 entries per request
#   - No pagination (no start/page parameter)
#   - Entries have: title, link, published, source (sometimes), summary
#
# Confirmed working Indian language codes for hl parameter:
#   hi (Hindi), ta (Tamil), te (Telugu), bn (Bengali), mr (Marathi),
#   gu (Gujarati), kn (Kannada), ml (Malayalam), pa (Punjabi)
#
# Unconfirmed for hl parameter (need validation):
#   or (Odia), as (Assamese), ur (Urdu), ne (Nepali)
#
# Note: en-IN is the correct code for English in India (not just "en")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pygooglenews library | Raw httpx + feedparser | 2024+ | pygooglenews unmaintained since 2021; raw approach is more reliable |
| Sync requests + feedparser | Async httpx fetch + sync feedparser parse | 2023+ | httpx provides native async; feedparser parse on string is fast enough to not need executor |
| abc.ABC for interfaces | typing.Protocol | Python 3.8+ (mature 3.10+) | Structural subtyping; no inheritance required; better IDE support |
| Google News direct article URLs | Google News redirect/encoded URLs | ~2023 | All URLs now go through news.google.com redirect; actual URL requires decoding |
| Simple base64 URL decoding | Server-side batchexecute decoding | July 2024 | New-style "AU_yqL" URLs require HTTP request to Google's batchexecute endpoint |

**Deprecated/outdated:**
- `pygooglenews`: Unmaintained since 2021. Do not use.
- Direct base64 URL decoding: No longer works for new-style Google News URLs (July 2024+). URLs must be decoded via Google's batchexecute endpoint or resolved via HTTP redirect following.

## Google News Language Support Matrix for India

Based on research, the following language codes are supported by Google News for India (`gl=IN`):

| Our Code | Google hl Code | Language | Confidence | Notes |
|----------|---------------|----------|------------|-------|
| en | en-IN | English | HIGH | Confirmed: news.google.com/home?hl=en-IN&gl=IN works |
| hi | hi | Hindi | HIGH | Confirmed: news.google.com/home?hl=hi&gl=IN works |
| ta | ta | Tamil | HIGH | Confirmed via SearchAPI docs and Google News interface |
| te | te | Telugu | HIGH | Confirmed via SearchAPI docs and Google News interface |
| bn | bn | Bengali | HIGH | Confirmed via SearchAPI docs and Google News interface |
| mr | mr | Marathi | HIGH | Confirmed via SearchAPI docs and Google News interface |
| gu | gu | Gujarati | HIGH | Confirmed via SearchAPI docs |
| kn | kn | Kannada | HIGH | Confirmed via SearchAPI docs and Google News interface |
| ml | ml | Malayalam | HIGH | Confirmed via SearchAPI docs and Google News interface |
| pa | pa | Punjabi | MEDIUM | Listed in SearchAPI docs but not in Google News Wikipedia languages |
| or | or | Odia | LOW | Not confirmed in any source; may not be supported |
| as | as | Assamese | LOW | Not confirmed in any source; may not be supported |
| ur | ur | Urdu | LOW | Not confirmed for gl=IN; may require gl=PK |
| ne | ne | Nepali | LOW | Not confirmed for gl=IN; may require gl=NP |

**Recommendation:** Build the language mapping but handle unsupported languages gracefully (return empty list, log a warning). The LOW-confidence languages should be validated at implementation time by making test requests.

## Monsoon Pipeline Lessons Learned

The monsoon pipeline (`/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/`) provides valuable lessons:

### What It Does Well
1. **Adaptive rate limiting:** The `SmartGoogleNewsHandler` tracks success rates per region/language and adjusts delays dynamically. This concept should inform Phase 6 (query engine), not Phase 4.
2. **Source name extraction from `entry.source.title`:** This pattern works and should be adopted.
3. **Date conversion from GMT to IST:** `convert_gmt_to_ist()` handles the RFC 822 format correctly. Our approach (feedparser `published_parsed` -> datetime(utc) -> ArticleRef validator -> IST) is cleaner.
4. **Resilience to query failures:** Continues processing even when individual queries fail. GoogleNewsSource.search() should never raise on HTTP errors.

### What to Avoid
1. **pygooglenews dependency:** Unmaintained, synchronous, masks the simple RSS URL construction.
2. **400+ line SmartGoogleNewsHandler:** Combines rate limiting, circuit breaker, session management, user agent rotation, query optimization, and banned patterns in one class. Phase 4 should be a thin adapter; rate limiting belongs in Phase 6, circuit breaker in Phase 9.
3. **Positional list indexing:** `entries.append([title, link, ist_date_str, source, summary, term, lang_code])` -- our ArticleRef model prevents this.
4. **Synchronous requests:** The monsoon pipeline is entirely synchronous. Our pipeline uses async from day one (prior decision [01-01]).

## Open Questions

1. **Which Indian languages does Google News RSS actually support?**
   - What we know: hi, ta, te, bn, mr, gu, kn, ml are confirmed. pa is likely. or, as, ur, ne are unconfirmed.
   - What's unclear: Whether queries with unsupported hl codes silently fall back to English or return errors/empty results.
   - Recommendation: Implement with all 14 language codes. Add a validation test that makes one request per language and records which ones return results. Log unsupported languages as warnings; do not crash.

2. **Should GoogleNewsSource own its httpx.AsyncClient or receive one?**
   - What we know: Creating a new client per request is wasteful (no connection pooling). Creating one at module level is inflexible.
   - What's unclear: Whether Phase 6 (query engine) will want to share a single client across all sources for connection pool management.
   - Recommendation: Accept an optional `httpx.AsyncClient` in the constructor. If none provided, create one internally. This gives Phase 6 flexibility while keeping Phase 4 self-contained. Use async context manager pattern (`async with`).

3. **How to handle the `state` field in ArticleRef when searching Google News?**
   - What we know: ArticleRef requires a `state` field. Google News RSS does not return state information -- it is inferred from the search query.
   - What's unclear: Who is responsible for setting the state: the caller of search() or GoogleNewsSource itself?
   - Recommendation: The caller (Phase 6 query engine) should pass state context. GoogleNewsSource.search() should accept state/search_term as parameters or the caller should set them after receiving results. Simplest approach: add `state` and `search_term` as parameters to `search()`, since they are caller context that the source cannot determine.

4. **Should the `search()` method signature include state and search_term?**
   - What we know: ArticleRef requires `state` and `search_term` fields. These are caller context, not search-result data.
   - What's unclear: Whether adding these to the Protocol makes it less clean for Phase 5 sources.
   - Recommendation: Include `state` and `search_term` in the `search()` signature since all sources need them to construct ArticleRefs. The alternative (having the caller post-process to add state/search_term) is error-prone and violates single-responsibility.

## Sources

### Primary (HIGH confidence)
- **feedparser 6.0.11 docs** - Entry fields, published_parsed, source attribute: https://feedparser.readthedocs.io/en/latest/common-rss-elements/ and https://feedparser.readthedocs.io/en/main/reference-entry-source/
- **feedparser GitHub #116** - Async strategy (maintainer recommends fetch separately, parse with feedparser): https://github.com/kurtmckee/feedparser/issues/116
- **Python typing.Protocol spec** - Structural subtyping: https://typing.python.org/en/latest/spec/protocol.html
- **Existing codebase** - ArticleRef model in `/Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/models/article.py`
- **Existing codebase** - Monsoon pipeline in `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/monsoon.py` and `smart_google_news_handler.py`

### Secondary (MEDIUM confidence)
- **NewsCatcher blog** - Google News RSS search parameters documentation: https://www.newscatcherapi.com/blog-posts/google-news-rss-search-parameters-the-missing-documentaiton
- **pygooglenews README** - URL construction reference: https://github.com/kotartemiy/pygooglenews
- **SearchAPI docs** - Google News hl parameter language codes: https://www.searchapi.io/docs/parameters/google-news/hl
- **Google News RSS Gist** - Entry field access patterns: https://gist.github.com/cyberandy/807d5623d842a44c6010af92c478963e
- **googlenewsdecoder PyPI** - URL decoding approach: https://pypi.org/project/googlenewsdecoder/
- **Google News URL decoder GitHub** - Base64/batchexecute decoding: https://github.com/SSujitX/google-news-url-decoder

### Tertiary (LOW confidence)
- **Google News rate limiting from GitHub Actions** - No direct evidence found for Google News RSS specifically; general 429 patterns apply
- **or/as/ur/ne language support** - Not confirmed by any authoritative source; needs runtime validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed; feedparser and httpx are well-documented; Protocol is stdlib
- Architecture: HIGH - Protocol pattern is well-established; httpx+feedparser bridge is recommended by feedparser maintainer; URL format confirmed by multiple sources
- Google News RSS parameters: MEDIUM - URL format confirmed by multiple reverse-engineering sources but no official Google documentation exists
- Indian language support: MEDIUM for confirmed languages (hi, ta, te, bn, mr, gu, kn, ml), LOW for unconfirmed (or, as, ur, ne)
- Pitfalls: HIGH - Identified from monsoon pipeline production experience, feedparser docs, and multiple web sources

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days -- feedparser/httpx are stable; Google News RSS URL format changes rarely but is undocumented)
