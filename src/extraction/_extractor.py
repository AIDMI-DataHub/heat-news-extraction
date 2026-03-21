"""Trafilatura-based article extraction with async bridge and batch processing.

Provides :func:`extract_article` (single) and :func:`extract_articles` (batch)
for converting :class:`~src.models.article.ArticleRef` objects into
:class:`~src.models.article.Article` objects with ``full_text`` populated.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from urllib.parse import urlparse

import httpx
import trafilatura

from src.extraction._resolver import resolve_url
from src.models.article import Article, ArticleRef

logger = logging.getLogger(__name__)

# ─── MSN domain skip (Issue 8) ──────────────────────────────────────

_SKIP_DOMAINS = frozenset({"msn.com"})


def _should_skip_url(url: str) -> bool:
    """Return True if URL belongs to a domain that never yields usable text."""
    try:
        netloc = urlparse(url).netloc.lower().removeprefix("www.")
        return any(netloc == d or netloc.endswith("." + d) for d in _SKIP_DOMAINS)
    except Exception:
        return False


# Boilerplate indicator phrases (case-insensitive substrings).
# If extracted text is short AND contains any of these, it's almost
# certainly nav/footer/banner content, not an article.
_BOILERPLATE_PHRASES = [
    "download app",
    "download the app",
    "डाउनलोड करें",
    "ऐप डाउनलोड",
    "all rights reserved",
    "terms of use",
    "privacy policy",
    "cookie policy",
    "subscribe to newsletter",
    "sign up for newsletter",
    "copyright ©",
    "© copyright",
    "trademark of",
    "registered trademark",
]


def _is_boilerplate(text: str) -> bool:
    """Return True if *text* looks like website boilerplate rather than article content."""
    if len(text.strip()) >= 500:
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in _BOILERPLATE_PHRASES)

# ─── Post-extraction text cleaning (Issues 4-6) ─────────────────────

_BREADCRUMB_RE = re.compile(r"^(?:\s*-\s+.{1,50}\n){2,}", re.MULTILINE)

_ALSO_READ_RE = re.compile(
    r"^\s*(?:Also\s+Read|Read\s+Also|ये\s+भी\s+पढ़ें|यह\s+भी\s+पढ़ें)"
    r"\s*[:|\-]?\s*.*$",
    re.MULTILINE | re.IGNORECASE,
)

_APP_PROMO_RE = re.compile(
    r"^\s*(?:Download\s+(?:the\s+)?app|Get\s+the\s+app|ऐप\s+डाउनलोड\s+करें).*$",
    re.MULTILINE | re.IGNORECASE,
)

_RECOMMENDED_RE = re.compile(
    r"(?:^.*(?:recommended|related\s+(?:news|articles|stories)"
    r"|संबंधित\s+खबरें|સંબંધિત\s+સમાચાર).*\n)(?:.+\n?){2,}$",
    re.MULTILINE | re.IGNORECASE,
)

_COPYRIGHT_RE = re.compile(
    r"\n\s*(?:©\s*\d{4}|copyright\s*©|[a-z]+ name,? logo).*$",
    re.IGNORECASE | re.DOTALL,
)


def _deduplicate_paragraphs(text: str) -> str:
    """Remove duplicate paragraphs, keeping first occurrence."""
    paragraphs = text.split("\n\n")
    seen: set[str] = set()
    unique: list[str] = []
    for para in paragraphs:
        key = para.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(para)
    return "\n\n".join(unique)


def _clean_text(text: str) -> str:
    """Strip content leakage: breadcrumbs, 'Also Read', app promos, recommended blocks, copyright."""
    text = _BREADCRUMB_RE.sub("", text)
    text = _ALSO_READ_RE.sub("", text)
    text = _APP_PROMO_RE.sub("", text)
    text = _RECOMMENDED_RE.sub("", text)
    text = _COPYRIGHT_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _deduplicate_paragraphs(text)
    return text.strip()


# ─── Geo-validation (Issue 3) ───────────────────────────────────────

_NON_INDIA_PLACES = [
    # US states
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
    # US cities commonly in weather news
    "phoenix", "denver", "las vegas", "houston", "dallas", "chicago",
    "los angeles", "san francisco", "miami", "seattle", "boston",
    "atlanta", "portland", "san antonio", "tucson", "sacramento",
    # Country/region markers
    "united states", "usa", "u.s.a", "u.s.",
    "united kingdom", "australia", "pakistan", "saudi arabia",
    "middle east", "europe", "european",
]

_NON_INDIA_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _NON_INDIA_PLACES) + r")\b",
    re.IGNORECASE,
)


def _is_non_india(title: str, text: str | None) -> bool:
    """Return True if article is clearly about a non-India location."""
    combined = title
    if text is not None:
        combined += " " + text[:1500]
    return bool(_NON_INDIA_RE.search(combined))


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}


async def _fetch_html(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch the HTML content of *url* with one retry on transient failure.

    Uses ``follow_redirects=True`` and a 15-second timeout (5-second
    connect).  Returns the decoded HTML string on success, or ``None``
    on any failure.  Never raises.
    """
    for attempt in range(2):
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
            response.raise_for_status()
            return response.text
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            logger.warning("Fetch failed for %s: %s", url, exc)
            return None
        except Exception:
            logger.error("Unexpected error fetching %s", url, exc_info=True)
            return None
    return None


async def _extract_text(html: str, url: str) -> str | None:
    """Extract article text from *html* using trafilatura.

    Tries ``favor_precision`` first for cleaner output, then falls back
    to ``favor_recall`` (more lenient) if precision yields nothing.

    Runs the synchronous ``trafilatura.extract()`` in a thread via
    :func:`asyncio.to_thread` so the event loop is not blocked.
    Returns the extracted text string, or ``None`` on failure.
    """
    try:
        # Try precision first (cleaner output)
        text: str | None = await asyncio.to_thread(
            trafilatura.extract,
            html,
            favor_precision=True,
            include_comments=False,
            include_tables=False,
            deduplicate=True,
            url=url,
        )
        # Fallback: favor_recall (more lenient, catches more content)
        if text is None:
            text = await asyncio.to_thread(
                trafilatura.extract,
                html,
                favor_recall=True,
                include_comments=False,
                include_tables=True,
                deduplicate=True,
                url=url,
            )
        # Clean content leakage before length/boilerplate checks
        if text is not None:
            text = _clean_text(text)
        # Discard very short extractions (likely ads, navbars, or footers)
        if text is not None and len(text.strip()) < 100:
            logger.warning("Extracted text too short (%d chars), discarding: %s", len(text.strip()), url)
            return None
        # Discard short boilerplate (app prompts, copyright notices, cookie banners)
        if text is not None and _is_boilerplate(text):
            logger.warning("Boilerplate detected (%d chars), discarding: %s", len(text.strip()), url)
            return None
        return text
    except Exception:
        logger.error("Trafilatura error for %s", url, exc_info=True)
        return None


async def extract_article(
    ref: ArticleRef, client: httpx.AsyncClient
) -> Article:
    """Extract full text for a single *ref*, returning an :class:`Article`.

    Steps:
    1. Resolve URL (Google News redirect -> actual URL).
    2. Fetch HTML from the resolved URL.
    3. Extract article text using trafilatura.
    4. Return an :class:`Article` with ``full_text`` populated (or ``None``).

    **Never raises** -- failures are logged and produce an Article with
    ``full_text=None`` (requirement EXTR-03).
    """
    # Step 0: Skip known-bad domains (Issue 8)
    if _should_skip_url(ref.url):
        logger.debug("Skipping known-bad domain: %s", ref.url)
        return Article(**ref.model_dump(), full_text=None, relevance_score=0.0)

    try:
        # Step 1: Resolve URL
        actual_url = await resolve_url(ref.url, client)

        # Step 2: Fetch HTML
        html = await _fetch_html(actual_url, client)
        if html is None:
            logger.warning("Fetch failed for %s (resolved: %s)", ref.url, actual_url)
            return Article(**ref.model_dump(), full_text=None, relevance_score=0.0)

        # Step 3: Extract text
        text = await _extract_text(html, actual_url)

        # Step 3b: Geo-validation (Issue 3)
        if text is not None and _is_non_india(ref.title, text):
            logger.info("Non-India article rejected: %s (state=%s)", actual_url, ref.state)
            text = None

        # Step 4: Build Article
        if text is not None:
            logger.info(
                "Extracted %d chars from %s", len(text), actual_url
            )
        else:
            logger.warning("No text extracted from %s", actual_url)

        return Article(**ref.model_dump(), full_text=text, relevance_score=0.0)

    except Exception:
        logger.error(
            "Unexpected error extracting %s", ref.url, exc_info=True
        )
        return Article(**ref.model_dump(), full_text=None, relevance_score=0.0)


async def extract_articles(
    refs: list[ArticleRef],
    max_concurrent: int = 10,
    deadline: float | None = None,
) -> list[Article]:
    """Batch-extract articles from a list of :class:`ArticleRef`.

    Creates a shared :class:`httpx.AsyncClient` and uses an
    :class:`asyncio.Semaphore` to bound concurrency at *max_concurrent*.

    Processes refs in chunks and checks the *deadline* (monotonic time)
    between chunks.  When the deadline is reached, remaining refs are
    returned as :class:`Article` objects with ``full_text=None``.

    Parameters
    ----------
    refs:
        Article references collected by the query engine.
    max_concurrent:
        Maximum number of concurrent extraction tasks.
    deadline:
        Optional monotonic time deadline.  When reached, extraction stops
        and unprocessed refs become Articles with ``full_text=None``.

    Returns
    -------
    list[Article]
        One :class:`Article` per input ref (order preserved).
    """
    if not refs:
        logger.info("No article refs to extract")
        return []

    articles: list[Article] = []
    chunk_size = max_concurrent * 3  # Process 30 at a time
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _extract_one(ref: ArticleRef) -> Article:
        async with semaphore:
            return await extract_article(ref, client)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(15.0, connect=5.0),
        headers=_HEADERS,
    ) as client:
        for i in range(0, len(refs), chunk_size):
            # Check deadline between chunks
            if deadline is not None and time.monotonic() >= deadline:
                logger.warning(
                    "Extraction deadline reached after %d/%d refs, stopping",
                    len(articles),
                    len(refs),
                )
                break

            chunk = refs[i : i + chunk_size]
            tasks = [_extract_one(ref) for ref in chunk]
            chunk_results: list[Article] = await asyncio.gather(
                *tasks, return_exceptions=False
            )
            articles.extend(chunk_results)

    # Fill remaining unprocessed refs as Articles with full_text=None
    if len(articles) < len(refs):
        skipped = len(refs) - len(articles)
        logger.info("Skipping extraction for %d remaining refs (deadline)", skipped)
        for ref in refs[len(articles) :]:
            articles.append(
                Article(**ref.model_dump(), full_text=None, relevance_score=0.0)
            )

    # Log batch summary
    successful = sum(1 for a in articles if a.full_text is not None)
    failed = len(articles) - successful
    logger.info(
        "Extraction complete: %d refs, %d extracted, %d failed/skipped",
        len(refs),
        successful,
        failed,
    )

    return articles
