"""GNews REST API source adapter.

Fetches news articles via the GNews ``/api/v4/search`` endpoint using
``httpx`` and maps JSON results to :class:`ArticleRef` objects.  This is
a tertiary news collection adapter for the heat news extraction pipeline.

Key design decisions
--------------------
* **Mirror GoogleNewsSource structure** -- constructor with optional client
  + timeout, async context manager, ``search()`` that never raises, lazy
  client creation via :meth:`_ensure_client`, and :meth:`close` for cleanup.
* **Daily quota tracking** -- simple in-memory counter (100 requests/day on
  free tier).  The pipeline runs once daily, so no persistence is needed.
* **Graceful no-key degradation** -- when the API key is missing, a warning
  is logged once at construction time and all ``search()`` calls return
  empty lists without making HTTP requests.
* **Language filtering** -- GNews supports only 8 of our 14 Indian languages
  (en, hi, bn, ta, te, mr, ml, pa).  Unsupported languages return empty
  results without making an HTTP request.
* **HTTP 403 = quota exhausted** -- GNews returns 403 (not 429) when the
  daily quota is exhausted.  HTTP 429 is for per-second rate limiting only.
* **Never raises from search()** -- all HTTP / parse errors are caught and
  logged; an empty list is returned on failure.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from src.models.article import ArticleRef

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GNews API base URL
# ---------------------------------------------------------------------------

_BASE_URL = "https://gnews.io/api/v4/search"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gnews_to_ref(
    article: dict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    """Convert a single GNews result dict to an :class:`ArticleRef`.

    Returns ``None`` if the result is missing required fields (title, url,
    or publishedAt), allowing the caller to skip it gracefully.
    """
    title = (article.get("title") or "").strip()
    url = (article.get("url") or "").strip()  # GNews uses "url", not "link"
    published_at = article.get("publishedAt")
    source = article.get("source", {})
    source_name = source.get("name", "Unknown")

    if not title or not url or not published_at:
        return None

    # GNews publishedAt format: "2026-02-10T08:30:00Z" (ISO 8601, always UTC).
    # Replace trailing "Z" with "+00:00" for fromisoformat().
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
    except Exception:  # noqa: BLE001
        logger.warning("Skipping article that failed ArticleRef validation: %s", title[:80])
        return None


# ---------------------------------------------------------------------------
# GNewsSource
# ---------------------------------------------------------------------------


class GNewsSource:
    """Fetches and parses GNews search results into ArticleRefs.

    Parameters
    ----------
    api_key:
        GNews API key.  If ``None`` or empty, the source returns empty
        results from every :meth:`search` call.
    client:
        Optional shared :class:`httpx.AsyncClient`.  If not provided, one
        will be created lazily on the first ``search()`` call and owned by
        this instance (closed via :meth:`close` or the async context manager).
    timeout:
        HTTP request timeout in seconds.
    """

    _SUPPORTED_LANGUAGES: set[str] = {
        "en", "hi", "bn", "ta", "te", "mr", "ml", "pa",
    }

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
        self._daily_count: int = 0
        self._daily_limit: int = 100
        if not api_key:
            logger.warning("GNews API key not provided; source will return empty results")

    # --- Async context manager -----------------------------------------------

    async def __aenter__(self) -> GNewsSource:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()

    # --- Core API ------------------------------------------------------------

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
        *,
        state: str = "",
        search_term: str = "",
    ) -> list[ArticleRef]:
        """Search GNews and return parsed :class:`ArticleRef` list.

        Never raises -- all HTTP and parse errors are caught, logged, and
        result in an empty list.
        """
        if not self._api_key:
            return []

        if language not in self._SUPPORTED_LANGUAGES:
            logger.debug("GNews does not support language %r, skipping", language)
            return []

        if self._daily_count >= self._daily_limit:
            logger.debug(
                "GNews daily limit reached (%d/%d)",
                self._daily_count,
                self._daily_limit,
            )
            return []

        params = {
            "apikey": self._api_key,
            "q": query,
            "lang": language,
            "country": country.lower(),
            "max": 10,
        }

        try:
            client = self._ensure_client()
            response = await client.get(_BASE_URL, params=params, timeout=self._timeout)
            self._daily_count += 1
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 403:
                # GNews returns 403 when daily quota is exhausted (not 429).
                self._daily_count = self._daily_limit
                logger.warning(
                    "GNews daily quota exhausted (HTTP 403) for query=%r lang=%s",
                    query,
                    language,
                )
            elif status == 429:
                logger.warning(
                    "GNews per-second rate limit hit (HTTP 429) for query=%r lang=%s",
                    query,
                    language,
                )
            elif status == 401:
                logger.error(
                    "Invalid GNews API key (HTTP 401) for query=%r lang=%s",
                    query,
                    language,
                )
            else:
                logger.warning(
                    "GNews HTTP %s for query=%r lang=%s",
                    status,
                    query,
                    language,
                )
            return []
        except httpx.TimeoutException:
            logger.warning(
                "GNews request timed out for query=%r lang=%s",
                query,
                language,
            )
            return []
        except httpx.RequestError as exc:
            logger.warning(
                "Network error fetching GNews for query=%r lang=%s: %s",
                query,
                language,
                exc,
            )
            return []

        # Parse JSON response.
        try:
            data = response.json()
        except Exception:  # noqa: BLE001
            logger.error(
                "Failed to parse GNews JSON for query=%r lang=%s",
                query,
                language,
                exc_info=True,
            )
            return []

        raw_articles = data.get("articles") or []

        articles: list[ArticleRef] = []
        skipped = 0
        for item in raw_articles:
            ref = _gnews_to_ref(item, language, state, search_term)
            if ref is not None:
                articles.append(ref)
            else:
                skipped += 1

        logger.info(
            "GNews query=%r lang=%s: %d articles parsed, %d entries skipped",
            query,
            language,
            len(articles),
            skipped,
        )
        return articles

    # --- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client if this instance owns it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- Private -------------------------------------------------------------

    def _ensure_client(self) -> httpx.AsyncClient:
        """Return the HTTP client, creating one lazily if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client
