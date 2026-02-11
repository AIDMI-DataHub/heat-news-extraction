# Phase 7: Article Extraction - Research

**Researched:** 2026-02-11
**Domain:** Web article text extraction, Google News URL resolution, Indian script handling, async/sync bridging
**Confidence:** HIGH

## Summary

Phase 7 extracts full article text from URLs collected by Phases 4-6. This involves two distinct technical challenges: (1) resolving Google News redirect URLs to actual article URLs, and (2) extracting article text using trafilatura. The pipeline stores results in the `Article` model's `full_text` field, converting `ArticleRef` instances into `Article` instances.

The core stack is already installed: trafilatura 2.0.0 handles text extraction with built-in encoding detection (via charset-normalizer), and httpx handles HTTP fetching. The main architectural challenge is bridging trafilatura's synchronous API with the pipeline's async design. Since trafilatura extraction is CPU-bound (parsing HTML, not I/O), `asyncio.to_thread` or `loop.run_in_executor` with a `ThreadPoolExecutor` is the correct bridge. For batch extraction of hundreds of articles, a bounded thread pool (4-8 workers) prevents resource exhaustion while maintaining throughput.

Google News redirect URLs (`news.google.com/rss/articles/...`) require resolution before trafilatura can extract content. There are two approaches: (a) the `googlenewsdecoder` library (makes HTTP requests to Google's batchexecute endpoint, rate-limited), or (b) implementing the decoding logic inline using httpx (fetch the article page from Google News, extract signature/timestamp, POST to batchexecute endpoint). The monsoon pipeline's approach of base64-decoding "CBMi"-prefixed URLs works for old-style URLs but fails for newer "AU_yqL"-prefixed URLs which require the batchexecute endpoint. Given the "no extra dependencies unless necessary" principle and the need for async support (which googlenewsdecoder lacks), the recommended approach is to implement a lightweight URL resolver using httpx that tries: (1) HTTP HEAD/GET with redirect following, (2) batchexecute decoding for URLs that don't resolve via redirect.

**Primary recommendation:** Use trafilatura's `extract()` with `favor_recall=True` for maximum content capture. Fetch HTML with httpx (async, already in the stack) and pass the downloaded HTML string to `trafilatura.extract()` via `asyncio.to_thread()`. Implement Google News URL resolution as a separate pre-processing step using httpx. Handle failures gracefully -- log and skip, never halt.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| trafilatura | 2.0.0 | Extract article text from HTML | Already installed; highest F1 (0.958) among OSS extractors; handles encoding detection |
| httpx | 0.28.1 | Async HTTP client for fetching pages and resolving URLs | Already installed; async-native; connection pooling; redirect following |
| pydantic | 2.10.6 | Article model with full_text field | Already installed; ArticleRef/Article models exist from Phase 2 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | stdlib | `to_thread()` for sync-to-async bridge | Running trafilatura.extract() from async context |
| concurrent.futures (stdlib) | stdlib | `ThreadPoolExecutor` for bounded parallelism | Batch extraction with controlled thread count |
| logging (stdlib) | stdlib | Structured extraction failure logging | Every failed extraction must be logged with URL and reason |
| charset-normalizer | (transitive) | Encoding detection for non-Latin scripts | Automatically used by trafilatura internally; handles Devanagari, Tamil, etc. |
| tenacity | 9.0.0 | Retry with backoff for transient HTTP failures | Already installed; wrap fetch calls for resilience |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| trafilatura | newspaper3k/newspaper4k | trafilatura has higher F1 (0.958 vs 0.949); newspaper4k requires lxml and is heavier; trafilatura already installed |
| trafilatura | readability-lxml | Lower accuracy; no metadata extraction; trafilatura already installed |
| Custom URL resolver | googlenewsdecoder | googlenewsdecoder is sync-only, adds dependency, uses requests (conflicts with httpx-only constraint); custom resolver with httpx is lightweight |
| asyncio.to_thread | loop.run_in_executor | to_thread is simpler API (Python 3.9+); run_in_executor allows custom executor for bounded pools -- use run_in_executor for batch processing |

**Installation:**
No additional packages needed. All requirements are already satisfied by Phase 1's `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  extraction/
    __init__.py           # Re-exports extract_articles, ArticleExtractor
    _resolver.py          # Google News URL resolver (httpx-based)
    _extractor.py         # Trafilatura wrapper with async bridge
```

### Pattern 1: Two-Step Extract (Resolve URL, Then Extract Text)
**What:** Separate URL resolution from text extraction. First resolve Google News redirect URLs to actual article URLs, then pass actual URLs to the extraction step.
**When to use:** For every article extraction. Google News URLs (the primary source) cannot be extracted directly -- trafilatura will get Google's redirect page, not the article.
**Example:**
```python
async def extract_article(ref: ArticleRef, client: httpx.AsyncClient) -> Article:
    """Extract full text from an ArticleRef, producing an Article."""
    # Step 1: Resolve URL if it's a Google News redirect
    actual_url = await resolve_url(ref.url, client)

    # Step 2: Fetch HTML
    html = await fetch_html(actual_url, client)
    if html is None:
        return Article(**ref.model_dump(), full_text=None)

    # Step 3: Extract text (sync trafilatura via thread)
    text = await asyncio.to_thread(trafilatura.extract, html, favor_recall=True)

    return Article(**ref.model_dump(), full_text=text)
```

### Pattern 2: ArticleRef to Article Conversion (Frozen Model Pattern)
**What:** Both ArticleRef and Article are frozen (immutable). Article extends ArticleRef. To create an Article from an ArticleRef, use `ref.model_dump()` to get a dict, then pass it to `Article(**dict, full_text=..., relevance_score=...)`.
**When to use:** Every time extraction produces a result.
**Example:**
```python
# ArticleRef is frozen -- cannot mutate. Create new Article instead.
ref: ArticleRef = ...  # from Phase 6 collection
article = Article(
    **ref.model_dump(),
    full_text=extracted_text,  # None if extraction failed
    relevance_score=0.0,       # Phase 8 will set this
)
```

### Pattern 3: Bounded Async Extraction with Semaphore
**What:** Use `asyncio.Semaphore` to limit concurrent extractions. Trafilatura is CPU-bound and thread-based; unlimited concurrency would exhaust threads and memory.
**When to use:** When processing a batch of ArticleRefs (potentially hundreds).
**Example:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Shared thread pool for trafilatura calls
_EXECUTOR = ThreadPoolExecutor(max_workers=8)

async def extract_batch(
    refs: list[ArticleRef],
    client: httpx.AsyncClient,
    max_concurrent: int = 10,
) -> list[Article]:
    """Extract articles with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _extract_one(ref: ArticleRef) -> Article:
        async with semaphore:
            return await extract_article(ref, client)

    tasks = [_extract_one(ref) for ref in refs]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Pattern 4: Google News URL Resolution via httpx
**What:** Resolve Google News redirect URLs to actual article URLs using HTTP redirect following, with batchexecute fallback.
**When to use:** Before passing URLs to trafilatura for extraction.
**Example:**
```python
async def resolve_google_news_url(url: str, client: httpx.AsyncClient) -> str:
    """Resolve a Google News redirect URL to the actual article URL.

    Strategy:
    1. Try following HTTP redirects (works for some URLs)
    2. Fall back to batchexecute endpoint for encoded URLs
    3. Return original URL if all else fails
    """
    if "news.google.com" not in url:
        return url  # Not a Google News URL, return as-is

    # Strategy 1: Follow redirects
    try:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        final_url = str(response.url)
        if "news.google.com" not in final_url:
            return final_url  # Successfully resolved
    except httpx.HTTPError:
        pass

    # Strategy 2: batchexecute decoding (for AU_yqL-style URLs)
    try:
        resolved = await _decode_via_batchexecute(url, client)
        if resolved:
            return resolved
    except Exception:
        pass

    return url  # Return original if all strategies fail
```

### Anti-Patterns to Avoid
- **Calling trafilatura.fetch_url():** This is synchronous and uses its own HTTP client (urllib3 internally). Use httpx to fetch HTML async, then pass the HTML string to `trafilatura.extract()`. This avoids blocking the event loop and leverages httpx's connection pooling.
- **Unbounded concurrency for extraction:** Do NOT `asyncio.gather()` 500 extraction tasks without a semaphore. Each extraction involves thread pool work and memory for HTML parsing. Use bounded concurrency (8-15 concurrent).
- **Mutating ArticleRef to add full_text:** ArticleRef is frozen. The design pattern is: create a NEW Article from ArticleRef's data. Use `ref.model_dump()` to copy fields.
- **Using browser automation for URL resolution:** Prior decision [01-01] explicitly bans Selenium/Playwright. Google News URLs can be resolved via HTTP requests to Google's endpoints.
- **Halting on extraction failure:** Requirement EXTR-03 mandates that failures are logged but do not halt the pipeline. Every extraction call must be wrapped in try/except.
- **Ignoring URL resolution failures:** If a Google News URL cannot be resolved, log it and create an Article with `full_text=None`. Do not retry indefinitely.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML text extraction | Custom BeautifulSoup article parser | `trafilatura.extract(html)` | trafilatura handles boilerplate removal, content detection, encoding -- 0.958 F1 vs manual parsing |
| Character encoding detection | Manual charset sniffing / chardet | `trafilatura.extract()` internally uses charset-normalizer | charset-normalizer is trafilatura's dependency; handles Indian scripts automatically |
| HTTP fetching with redirect following | `trafilatura.fetch_url()` (sync) | `httpx.AsyncClient.get(url, follow_redirects=True)` | httpx is already the pipeline's HTTP client; async-native; connection pooling |
| Retry logic for HTTP failures | Custom retry loops | `tenacity.retry` decorator | tenacity 9.0.0 already installed; handles exponential backoff with jitter |
| URL normalization for dedup | Custom regex URL cleaners | Defer to Phase 8 (DEDU-01) | URL normalization is Phase 8 scope; Phase 7 just extracts text |
| Language detection from extracted text | Custom Unicode range counting | Defer to Phase 8 or use trafilatura's `target_language` param | trafilatura can filter by language if needed; language is already known from ArticleRef |

**Key insight:** The monsoon pipeline's `article_scraper.py` is 1000+ lines with Selenium, Playwright, newspaper3k, BeautifulSoup, process pools, Chrome driver management, and custom URL decoders. The heat pipeline replaces ALL of this with ~150 lines: httpx fetch + trafilatura extract + asyncio thread bridge. The difference is the "no browser" constraint and trafilatura's quality, which eliminates 90% of the complexity.

## Common Pitfalls

### Pitfall 1: Google News URLs Yield Google's Page, Not Article Content
**What goes wrong:** Passing a `news.google.com/rss/articles/...` URL directly to trafilatura returns Google's redirect/consent page HTML, not the actual article.
**Why it happens:** Google News URLs are encoded redirect URLs. Since mid-2023, they use a new encoding format that cannot be decoded by simple base64.
**How to avoid:** Always resolve Google News URLs to actual article URLs BEFORE extraction. Implement a two-strategy resolver: (1) HTTP redirect following, (2) batchexecute endpoint decoding.
**Warning signs:** Extracted text contains "Before you continue to Google" or "news.google.com" content instead of article text.

### Pitfall 2: Blocking the Event Loop with Trafilatura
**What goes wrong:** Calling `trafilatura.extract()` directly in an async function blocks the entire event loop for the duration of HTML parsing (can be 100ms-2s per article).
**Why it happens:** trafilatura is entirely synchronous. It uses lxml for HTML parsing, which is CPU-bound C code. Python's GIL means CPU-bound work in threads still serializes, but I/O and other async tasks can proceed.
**How to avoid:** Use `asyncio.to_thread(trafilatura.extract, html, ...)` or `loop.run_in_executor(executor, trafilatura.extract, html)` for every extraction call. For batch processing, use a bounded `ThreadPoolExecutor` to prevent thread explosion.
**Warning signs:** Other async tasks (HTTP fetches, logging) stall during extraction bursts.

### Pitfall 3: Memory Exhaustion from Large HTML Documents
**What goes wrong:** Some news sites serve HTML pages of 2-10MB (ads, inline scripts, embedded media). Loading hundreds into memory simultaneously causes OOM, especially in GitHub Actions (7GB limit).
**Why it happens:** trafilatura parses the entire HTML tree into an lxml.etree. Concurrent extraction multiplies memory usage.
**How to avoid:** Set `max_tree_size` in trafilatura's extract call to limit parsed tree nodes. Use bounded concurrency (semaphore). Check response `Content-Length` before downloading -- skip HTML over 5MB. Use trafilatura's `no_fallback=True` for faster extraction with less memory.
**Warning signs:** GitHub Actions workflow killed by OOM; extraction slows to a crawl.

### Pitfall 4: Indian Script Mojibake in Extracted Text
**What goes wrong:** Hindi/Tamil/Telugu article text appears as garbled characters (e.g., `à¤¹à¥à¤Ÿ` instead of `हीट`).
**Why it happens:** The HTML page declares one charset (e.g., ISO-8859-1) but serves UTF-8 content, or the HTTP response has no charset header and trafilatura's charset-normalizer guesses wrong.
**How to avoid:** Trafilatura 2.0.0 uses charset-normalizer internally, which handles most cases. If mojibake is detected post-extraction, the `ftfy` library can repair common encoding errors. However, do NOT add ftfy as a dependency preemptively -- only if mojibake is observed in testing. The key prevention is: fetch HTML with httpx (which respects charset headers) and pass the decoded string (not bytes) to trafilatura.
**Warning signs:** Extracted text for Hindi/Tamil articles contains Latin-looking characters with diacritical marks; text length is suspiciously long for the article.

### Pitfall 5: Rate Limiting from Google's batchexecute Endpoint
**What goes wrong:** Resolving many Google News URLs via batchexecute triggers HTTP 429 (Too Many Requests), causing URL resolution to fail for the batch.
**Why it happens:** Google rate-limits the batchexecute endpoint. From GitHub Actions shared IPs, the threshold is lower.
**How to avoid:** Add delays between batchexecute requests (1-2 seconds). Process URL resolution in small batches (10-20 at a time). If 429 is received, back off exponentially (use tenacity). Accept that some URLs will not resolve -- create Article with `full_text=None` for those.
**Warning signs:** Bursts of 429 responses from `news.google.com/_/DotsSplashUi/data/batchexecute`.

### Pitfall 6: Timeouts on Slow Indian News Sites
**What goes wrong:** Some Indian regional news sites (especially smaller regional-language outlets) respond very slowly (10-30 seconds) or not at all, causing the pipeline to stall.
**Why it happens:** Smaller sites have limited server capacity. Geographic distance from GitHub Actions runners (US/EU) to Indian servers adds latency.
**How to avoid:** Set aggressive timeouts: 15 seconds for HTTP fetch, 30 seconds for extraction. Use `httpx.AsyncClient` with `timeout=httpx.Timeout(15.0, connect=5.0)`. For extraction, set trafilatura's `config` with `DOWNLOAD_TIMEOUT=15`. Log timeouts with the URL for later analysis.
**Warning signs:** Pipeline taking 30+ minutes for extraction; many articles timing out from the same domain.

### Pitfall 7: Frozen Model Prevents ArticleRef Mutation
**What goes wrong:** Attempting to set `full_text` on an `ArticleRef` instance raises `ValidationError` because `ArticleRef` has `frozen=True`.
**Why it happens:** Phase 2 design decision: both models are immutable. The intended pattern is to create a NEW `Article` from `ArticleRef` data.
**How to avoid:** Use `Article(**ref.model_dump(), full_text=extracted_text)` to create a new Article. Never try to mutate an ArticleRef.
**Warning signs:** `pydantic_core._pydantic_core.ValidationError: Instance is frozen`.

## Code Examples

Verified patterns from official sources and codebase analysis:

### Trafilatura Extract with Favor Recall
```python
# Source: https://trafilatura.readthedocs.io/en/latest/usage-python.html
import trafilatura

# For news articles, favor_recall=True captures more content
# (may include some non-article text, but better than missing paragraphs)
text = trafilatura.extract(
    html_string,
    favor_recall=True,      # Maximize content capture
    include_comments=False,  # Skip comment sections
    include_tables=True,     # Keep data tables (weather data, statistics)
    deduplicate=True,        # Remove repeated paragraphs
    url=actual_url,          # Helps trafilatura with relative URL resolution
)
# Returns: str or None
```

### Async Fetch + Sync Extract Bridge
```python
# Source: Python asyncio docs + trafilatura API
import asyncio
import httpx
import trafilatura

async def fetch_and_extract(
    url: str,
    client: httpx.AsyncClient,
) -> str | None:
    """Fetch HTML async, extract text in thread."""
    try:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
        html = response.text  # httpx decodes based on charset header
    except httpx.HTTPError as exc:
        logger.warning("HTTP error fetching %s: %s", url, exc)
        return None

    # Run sync trafilatura in a thread to avoid blocking event loop
    text = await asyncio.to_thread(
        trafilatura.extract,
        html,
        favor_recall=True,
        include_comments=False,
        include_tables=True,
        deduplicate=True,
        url=url,
    )
    return text
```

### Google News URL Resolution via batchexecute
```python
# Source: https://gist.github.com/huksley/bc3cb046157a99cd9d1517b32f91a99e
# Adapted for httpx (async) and the heat pipeline

import json
from urllib.parse import quote, urlparse
from lxml import html as lxml_html  # trafilatura's dependency, already available

async def _get_decoding_params(
    gn_art_id: str, client: httpx.AsyncClient
) -> dict[str, str] | None:
    """Fetch signature and timestamp needed for batchexecute decoding."""
    try:
        response = await client.get(
            f"https://news.google.com/rss/articles/{gn_art_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        tree = lxml_html.fromstring(response.text)
        div = tree.cssselect("c-wiz > div")
        if not div:
            return None
        return {
            "signature": div[0].get("data-n-a-sg", ""),
            "timestamp": div[0].get("data-n-a-ts", ""),
            "gn_art_id": gn_art_id,
        }
    except Exception:
        return None


async def _decode_via_batchexecute(
    url: str, client: httpx.AsyncClient
) -> str | None:
    """Decode a Google News URL via Google's batchexecute endpoint."""
    gn_art_id = urlparse(url).path.split("/")[-1]
    params = await _get_decoding_params(gn_art_id, client)
    if not params:
        return None

    payload_inner = (
        f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",'
        f'null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,'
        f'null,0,0,null,0],"{params["gn_art_id"]}",'
        f'{params["timestamp"]},"{params["signature"]}"]'
    )
    payload = f"f.req={quote(json.dumps([[['Fbv4je', payload_inner]]]))})"

    try:
        response = await client.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            content=payload,
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        # Parse response: skip first line, parse JSON
        parts = response.text.split("\n\n", 1)
        if len(parts) < 2:
            return None
        data = json.loads(parts[1])
        return json.loads(data[0][2])[1]
    except Exception:
        return None
```

### ArticleRef to Article Conversion
```python
# Source: Codebase analysis of src/models/article.py
from src.models.article import Article, ArticleRef

def ref_to_article(ref: ArticleRef, full_text: str | None = None) -> Article:
    """Convert an ArticleRef to an Article with optional full text.

    ArticleRef is frozen, so we create a new Article from its data.
    Article inherits all ArticleRef fields and adds full_text + relevance_score.
    """
    return Article(
        **ref.model_dump(),
        full_text=full_text,
        relevance_score=0.0,  # Set by Phase 8
    )
```

### Extraction Result Logging
```python
# Pattern for EXTR-03: failed extractions logged but don't halt pipeline
import logging

logger = logging.getLogger(__name__)

async def safe_extract(ref: ArticleRef, client: httpx.AsyncClient) -> Article:
    """Extract article text, logging failures without raising."""
    try:
        actual_url = await resolve_url(ref.url, client)
        text = await fetch_and_extract(actual_url, client)

        if text is None:
            logger.warning(
                "Extraction returned no text: url=%s resolved=%s",
                ref.url, actual_url,
            )
        else:
            logger.info(
                "Extracted %d chars from %s", len(text), actual_url,
            )

        return Article(**ref.model_dump(), full_text=text)

    except httpx.TimeoutException:
        logger.warning("Timeout extracting %s", ref.url)
        return Article(**ref.model_dump(), full_text=None)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %s extracting %s", exc.response.status_code, ref.url,
        )
        return Article(**ref.model_dump(), full_text=None)
    except Exception:
        logger.error("Unexpected error extracting %s", ref.url, exc_info=True)
        return Article(**ref.model_dump(), full_text=None)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| newspaper3k + BeautifulSoup + Selenium fallback | trafilatura (single library) | 2023+ | trafilatura's 0.958 F1 eliminates need for multi-library fallback chains |
| Sync requests + ProcessPoolExecutor | Async httpx fetch + ThreadPoolExecutor for extraction | 2024+ | Better resource utilization; no process serialization overhead |
| Base64 decoding of Google News URLs | batchexecute endpoint + HTTP redirect following | July 2024 | Old "CBMi" base64 method fails for new "AU_yqL" URLs |
| Multiple extraction libraries as fallbacks | trafilatura `favor_recall=True` | trafilatura 1.x+ | favor_recall mode captures content that previously needed fallback libraries |
| Manual charset detection (chardet) | charset-normalizer (built into trafilatura) | 2022+ | charset-normalizer is faster, more accurate, and already a transitive dependency |

**Deprecated/outdated:**
- `newspaper3k`: Superseded by newspaper4k; neither needed when trafilatura is available
- `trafilatura.fetch_url()` for async pipelines: Use httpx to fetch, then pass HTML to `extract()`. fetch_url is sync-only.
- Direct base64 decoding of Google News URLs: Only works for old-style "CBMi" URLs; new "AU_yqL" URLs require batchexecute endpoint

## Trafilatura Configuration for Indian News Sites

### Recommended Settings
```python
# For the heat pipeline, these settings maximize extraction quality:
text = trafilatura.extract(
    html,
    favor_recall=True,       # Don't miss article paragraphs
    include_comments=False,   # Skip user comments
    include_tables=True,      # Keep weather/temperature data tables
    deduplicate=True,         # Remove repeated content (common in Indian sites)
    no_fallback=False,        # Keep fallback algorithms (improves recall)
    url=url,                  # Helps with relative URL resolution
)
```

### Indian Script Encoding Handling
Trafilatura uses `charset-normalizer` (a dependency) for encoding detection. charset-normalizer:
- Analyzes byte patterns using statistical models for dozens of languages
- Supports all Indian scripts (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Gurmukhi)
- Defaults to UTF-8 when uncertain (correct for 98.9% of web)

**Key safeguard:** httpx decodes HTTP responses using the charset from the Content-Type header or charset-normalizer fallback. Passing `response.text` (a Python str, already decoded) to `trafilatura.extract()` means encoding is already handled. The critical path is: bytes -> httpx decodes to str -> trafilatura parses str. No raw bytes reach trafilatura.

### Performance Expectations
Based on trafilatura benchmarks (750 documents):
- Standard mode: 0.909 F1, 0.914 precision, 0.904 recall
- Precision mode (`favor_precision=True`): 0.902 F1, 0.932 precision, 0.874 recall
- Speed: ~4.8-9.4x baseline (significantly faster than newspaper3k or readabilipy)

**Note:** These benchmarks are primarily on German/English content. Indian language site performance is LOW confidence (not benchmarked), though the extraction algorithm is language-agnostic (operates on HTML structure, not text content).

## Google News URL Resolution Strategy

### URL Types
1. **Old-style (`CBMi...`):** Base64-encoded protobuf containing the actual URL. Can be decoded locally without HTTP requests.
2. **New-style (`AU_yqL...`):** Requires two HTTP requests to Google: (a) fetch article page for signature/timestamp, (b) POST to batchexecute for decoded URL.
3. **Direct redirect:** Some Google News URLs HTTP-redirect to the actual article URL when accessed.

### Recommended Resolution Strategy
```
For each Google News URL:
1. Try HTTP GET with follow_redirects=True (fastest, no decoding needed)
   - If final URL is not news.google.com -> SUCCESS
2. Try batchexecute decoding (two HTTP requests)
   - If decoded URL returned -> SUCCESS
3. Log failure, set full_text=None -> GRACEFUL FAILURE
```

### Rate Limiting Considerations
- batchexecute endpoint: ~1-2 second delay between requests recommended
- From GitHub Actions shared IPs: may need longer delays
- Use tenacity retry with exponential backoff on 429 responses
- Accept partial failure: not all URLs need to resolve for the pipeline to succeed

## Open Questions

1. **What percentage of Google News URLs can be resolved without batchexecute?**
   - What we know: Some URLs HTTP-redirect directly. The proportion is unclear.
   - What's unclear: Whether the simple redirect approach works for most URLs, or only a minority.
   - Recommendation: Implement both strategies. Measure redirect-resolution success rate during initial testing. If >80% resolve via redirect, the batchexecute fallback is a minor path.

2. **Does trafilatura extract well from major Indian news sites?**
   - What we know: trafilatura's benchmarks are primarily European/English content. Its algorithm is structure-based (not language-dependent), so it should work on any well-structured HTML.
   - What's unclear: Major Indian sites like Times of India, NDTV, The Hindu, Dainik Jagran may have unusual HTML structures or heavy ad injection that affects extraction quality.
   - Recommendation: During implementation, manually test extraction on 5-10 articles each from the top 5 Indian news sites. If extraction quality is poor for specific sites, investigate `prune_xpath` configuration to exclude problematic HTML regions.

3. **Should we resolve NewsData.io and GNews URLs too?**
   - What we know: Phase 4 Google News stores redirect URLs. Phase 5 NewsData.io and GNews store actual article URLs directly.
   - What's unclear: Whether any NewsData.io or GNews URLs are also redirects.
   - Recommendation: Apply URL resolution only to URLs containing `news.google.com`. Pass other URLs directly to extraction. If extraction fails on non-Google URLs, log and move on.

4. **How many articles can be extracted within the 45-minute GitHub Actions window?**
   - What we know: The pipeline collects potentially hundreds of articles per run. Each extraction involves: URL resolution (0-5s), HTTP fetch (1-15s), trafilatura parse (0.1-2s).
   - What's unclear: Total extraction time depends on article count, site responsiveness, and URL resolution success rate.
   - Recommendation: Design for throughput. Use bounded concurrency (8-10 parallel extractions). Set aggressive timeouts (15s fetch, 30s total per article). Phase 10 will enforce the 45-minute budget with graceful early termination.

5. **lxml dependency for batchexecute URL resolution (cssselect)**
   - What we know: The batchexecute approach needs to parse HTML to extract `data-n-a-sg` and `data-n-a-ts` attributes. The gist uses BeautifulSoup with lxml parser.
   - What's unclear: Whether lxml (already a trafilatura transitive dependency) provides cssselect, or if we need an alternative parser.
   - Recommendation: lxml is available as a transitive dependency of trafilatura. Use `lxml.html.fromstring()` and `.cssselect()` for parsing the Google News article page. If cssselect is not available, fall back to `lxml.html.fromstring()` with XPath: `tree.xpath("//c-wiz/div")`. Avoid adding BeautifulSoup as a dependency.

## Sources

### Primary (HIGH confidence)
- **trafilatura 2.0.0 official docs** - Python usage, extract() API, settings: https://trafilatura.readthedocs.io/en/latest/usage-python.html
- **trafilatura 2.0.0 core functions** - Complete function signatures: https://trafilatura.readthedocs.io/en/latest/corefunctions.html
- **trafilatura 2.0.0 settings** - Configuration options, download params, extraction params: https://trafilatura.readthedocs.io/en/latest/settings.html
- **trafilatura 2.0.0 evaluation** - Benchmark F1 scores, comparison with alternatives: https://trafilatura.readthedocs.io/en/latest/evaluation.html
- **Python asyncio docs** - to_thread, run_in_executor: https://docs.python.org/3/library/asyncio-task.html
- **Existing codebase** - ArticleRef/Article models in `src/models/article.py`, extraction `__init__.py` placeholder in `src/extraction/__init__.py`
- **Phase 4 research** - Google News URL format, deferred URL resolution decision: `.planning/phases/04-google-news-rss-source/04-RESEARCH.md`

### Secondary (MEDIUM confidence)
- **Google News URL decoder gist** - batchexecute decoding implementation: https://gist.github.com/huksley/bc3cb046157a99cd9d1517b32f91a99e
- **googlenewsdecoder PyPI** - URL decoding library (sync-only): https://pypi.org/project/googlenewsdecoder/
- **google-news-url-decoder GitHub** - Decoder implementation details: https://github.com/SSujitX/google-news-url-decoder
- **charset-normalizer docs** - Encoding detection algorithm: https://charset-normalizer.readthedocs.io/
- **trafilatura GitHub issue #262** - Parallel extraction performance: https://github.com/adbar/trafilatura/issues/262
- **trafilatura GitHub issue #305** - charset-normalizer integration: https://github.com/adbar/trafilatura/issues/305
- **Monsoon pipeline** - article_scraper.py extraction patterns, Google News URL handling: `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/article_scraper.py`

### Tertiary (LOW confidence)
- **trafilatura on Indian news sites** - No published benchmarks found; extraction quality on Indian sites is untested/unverified
- **Google News batchexecute rate limits** - No official documentation; limits observed empirically by community
- **httpx redirect following for Google News** - Unclear what percentage of Google News URLs resolve via standard HTTP redirects

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - trafilatura 2.0.0 and httpx 0.28.1 are already installed; APIs verified via official docs
- Architecture (async/sync bridge): HIGH - asyncio.to_thread and run_in_executor are standard Python patterns; well-documented
- Google News URL resolution: MEDIUM - batchexecute approach verified via multiple community sources, but Google's undocumented API may change
- Indian script handling: MEDIUM - charset-normalizer handles encoding detection; trafilatura is language-agnostic; but no Indian-language-specific benchmarks exist
- Pitfalls: HIGH - Identified from monsoon pipeline production experience, trafilatura docs, GitHub issues, and community sources

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days -- trafilatura/httpx are stable; Google News URL encoding may change without notice)
