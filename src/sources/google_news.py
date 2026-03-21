"""Google News RSS source adapter.

Fetches Google News RSS search results via ``httpx`` and parses them with
``feedparser`` into :class:`ArticleRef` objects.  This is the primary news
collection adapter for the heat news extraction pipeline.

Key design decisions
--------------------
* **httpx + feedparser** instead of ``pygooglenews`` (unmaintained since 2021).
* **No URL resolution** -- Google News redirect URLs are stored as-is;
  actual article URL resolution is a Phase 7 concern.
* **feedparser.parse() on response text** is pure CPU work (no I/O), so
  no ``run_in_executor`` is needed for RSS-sized payloads.
* **Never raises from search()** -- all HTTP / parse errors are caught and
  logged; an empty list is returned on failure.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from src.models.article import ArticleRef

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google News RSS base URL
# ---------------------------------------------------------------------------

_BASE_URL = "https://news.google.com/rss/search"

# ---------------------------------------------------------------------------
# Language code mapping: our ISO 639-1 codes -> Google News ``hl`` parameter.
#
# Uses bare ``en`` for English (matching pygooglenews upstream).  With
# ``gl=IN`` already set, Google News returns India-targeted results.
# All Indian languages use their bare ISO 639-1 codes.
# ---------------------------------------------------------------------------

_LANG_TO_HL: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "or": "or",
    "pa": "pa",
    "as": "as",
    "ur": "ur",
    "ne": "ne",
}

# ---------------------------------------------------------------------------
# Non-India publisher names to exclude from results.
#
# These are US/international weather outlets whose articles regularly appear
# in India-targeted Google News RSS results for heat-related queries (e.g.
# "Phoenix heatwave" from FOX Weather matching a search for "heatwave
# Rajasthan").  Filtering at the source level prevents wasted extraction
# and LLM budget on clearly irrelevant articles.
# ---------------------------------------------------------------------------

_EXCLUDED_SOURCES: frozenset[str] = frozenset({
    # US TV / weather outlets -- these almost never cover India heat news
    "FOX Weather",
    "Fox Weather",
    "The Weather Channel",
    "Weather Channel",
    "AccuWeather",
    "Weather.com",
    "USA TODAY",
    "USA Today",
    # US local TV stations
    "KUSA",
    "KUSA.com",
    "WFAA",
    "KHOU",
    "KVUE",
    "WFLA",
    "12News",
    "azcentral",
    "AZCentral",
    # US TV networks (rarely cover India-specific heat)
    "Fox News",
    "CBS News",
    "NBC News",
    "ABC News",
    "MSNBC",
    # US newspapers
    "New York Post",
    "Chicago Tribune",
    "Los Angeles Times",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_url(query: str, language: str, country: str, *, when: str = "7d") -> str:
    """Build a Google News RSS search URL.

    Mirrors the URL format used by pygooglenews, including the ``when:``
    temporal filter that restricts results to the specified time window::

        https://news.google.com/rss/search?q={query}+when:7d&ceid={country}:{lang}&hl={lang}&gl={country}

    The ``when`` parameter is appended directly to the query string (not as
    a URL parameter) — this is how Google News RSS interprets temporal
    filters.

    Uses :func:`urllib.parse.quote_plus` for proper Unicode encoding of
    non-Latin search terms (Devanagari, Tamil, etc.).
    """
    # Append temporal filter to query before encoding, matching pygooglenews
    full_query = f"{query} when:{when}" if when else query
    encoded_query = quote_plus(full_query)
    hl = _LANG_TO_HL.get(language, language)
    return (
        f"{_BASE_URL}"
        f"?q={encoded_query}"
        f"&ceid={country}:{hl}"
        f"&hl={hl}"
        f"&gl={country}"
    )


def _entry_to_article_ref(
    entry: feedparser.FeedParserDict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    """Convert a single feedparser entry to an :class:`ArticleRef`.

    Returns ``None`` if the entry is missing required fields (title, link,
    or publication date), allowing the caller to skip it gracefully.
    """
    title: str = getattr(entry, "title", "") or ""
    link: str = getattr(entry, "link", "") or ""
    if not title or not link:
        return None

    # --- Source name ---
    source_name = ""
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        source_name = entry.source.title
    elif " - " in title:
        # Google News often appends " - Publisher Name" to the title.
        source_name = title.rsplit(" - ", 1)[-1].strip()

    if not source_name:
        source_name = "Unknown"

    # --- Publication date ---
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        return None
    t = entry.published_parsed
    utc_dt = datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=timezone.utc)

    # ArticleRef's field_validator will convert UTC -> IST automatically.
    try:
        return ArticleRef(
            title=title,
            url=link,
            source=source_name,
            date=utc_dt,
            language=language,
            state=state,
            search_term=search_term,
        )
    except Exception:  # noqa: BLE001
        # Pydantic validation failure (e.g. title too long, bad language code)
        logger.warning("Skipping entry that failed ArticleRef validation: %s", title[:80])
        return None


# ---------------------------------------------------------------------------
# GoogleNewsSource
# ---------------------------------------------------------------------------


class GoogleNewsSource:
    """Fetches and parses Google News RSS search results into ArticleRefs.

    Parameters
    ----------
    client:
        Optional shared :class:`httpx.AsyncClient`.  If not provided, one
        will be created lazily on the first ``search()`` call and owned by
        this instance (closed via :meth:`close` or the async context manager).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout

    # --- Async context manager -------------------------------------------

    async def __aenter__(self) -> GoogleNewsSource:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()

    # --- Core API --------------------------------------------------------

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
        *,
        state: str = "",
        search_term: str = "",
    ) -> list[ArticleRef]:
        """Search Google News RSS and return parsed :class:`ArticleRef` list.

        Never raises -- all HTTP and parse errors are caught, logged, and
        result in an empty list.
        """
        url = _build_url(query, language, country)
        logger.debug("Fetching Google News RSS: %s", url)

        try:
            client = self._ensure_client()
            response = await client.get(url, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                from src.reliability._retry import RateLimitError

                raise RateLimitError(status_code=429, source="google_news") from exc
            logger.warning(
                "Google News returned HTTP %s for query=%r lang=%s: %s",
                exc.response.status_code,
                query,
                language,
                exc,
            )
            return []
        except httpx.TimeoutException:
            logger.warning(
                "Google News request timed out for query=%r lang=%s",
                query,
                language,
            )
            return []
        except httpx.RequestError as exc:
            logger.warning(
                "Network error fetching Google News for query=%r lang=%s: %s",
                query,
                language,
                exc,
            )
            return []
        except Exception:  # noqa: BLE001
            logger.error(
                "Unexpected error fetching Google News for query=%r lang=%s",
                query,
                language,
                exc_info=True,
            )
            return []

        # Parse RSS XML (sync, but near-instant for RSS-sized payloads).
        try:
            feed = feedparser.parse(response.text)
        except Exception:  # noqa: BLE001
            logger.error(
                "feedparser failed for query=%r lang=%s",
                query,
                language,
                exc_info=True,
            )
            return []

        articles: list[ArticleRef] = []
        skipped = 0
        source_filtered = 0
        for entry in feed.entries:
            ref = _entry_to_article_ref(entry, language, state, search_term)
            if ref is None:
                skipped += 1
                continue
            # Drop articles from known non-India publishers
            if ref.source in _EXCLUDED_SOURCES:
                source_filtered += 1
                continue
            articles.append(ref)

        if source_filtered:
            logger.info(
                "Google News query=%r lang=%s: filtered %d non-India source articles",
                query,
                language,
                source_filtered,
            )
        logger.info(
            "Google News query=%r lang=%s: %d articles parsed, %d entries skipped",
            query,
            language,
            len(articles),
            skipped,
        )
        return articles

    # --- Lifecycle -------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client if this instance owns it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- Private ---------------------------------------------------------

    def _ensure_client(self) -> httpx.AsyncClient:
        """Return the HTTP client, creating one lazily if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(follow_redirects=True)
        return self._client
