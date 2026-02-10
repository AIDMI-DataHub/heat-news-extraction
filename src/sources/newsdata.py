"""NewsData.io REST API source adapter.

Fetches the latest news articles via the NewsData.io ``/api/1/latest``
endpoint using ``httpx`` and maps JSON results to :class:`ArticleRef`
objects.  This is a secondary news collection adapter for the heat news
extraction pipeline.

Key design decisions
--------------------
* **Mirror GoogleNewsSource structure** -- constructor with optional client
  + timeout, async context manager, ``search()`` that never raises, lazy
  client creation via :meth:`_ensure_client`, and :meth:`close` for cleanup.
* **Daily quota tracking** -- simple in-memory counter (200 requests/day on
  free tier).  The pipeline runs once daily, so no persistence is needed.
* **Graceful no-key degradation** -- when the API key is missing, a warning
  is logged once at construction time and all ``search()`` calls return
  empty lists without making HTTP requests.
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
# NewsData.io API base URL
# ---------------------------------------------------------------------------

_BASE_URL = "https://newsdata.io/api/1/latest"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _newsdata_to_ref(
    article: dict,
    language: str,
    state: str,
    search_term: str,
) -> ArticleRef | None:
    """Convert a single NewsData.io result dict to an :class:`ArticleRef`.

    Returns ``None`` if the result is missing required fields (title, link,
    or pubDate), allowing the caller to skip it gracefully.
    """
    title = (article.get("title") or "").strip()
    link = (article.get("link") or "").strip()
    pub_date_str = article.get("pubDate")
    source_name = article.get("source_name") or article.get("source_id") or "Unknown"

    if not title or not link or not pub_date_str:
        return None

    # NewsData.io pubDate format: "2026-02-10 08:30:00" (space, no T).
    # Python's datetime.fromisoformat() handles this since 3.11.
    try:
        dt = datetime.fromisoformat(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)  # Assume UTC if naive
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
    except Exception:  # noqa: BLE001
        logger.warning("Skipping article that failed ArticleRef validation: %s", title[:80])
        return None


# ---------------------------------------------------------------------------
# NewsDataSource
# ---------------------------------------------------------------------------


class NewsDataSource:
    """Fetches and parses NewsData.io search results into ArticleRefs.

    Parameters
    ----------
    api_key:
        NewsData.io API key.  If ``None`` or empty, the source returns
        empty results from every :meth:`search` call.
    client:
        Optional shared :class:`httpx.AsyncClient`.  If not provided, one
        will be created lazily on the first ``search()`` call and owned by
        this instance (closed via :meth:`close` or the async context manager).
    timeout:
        HTTP request timeout in seconds.
    """

    _SUPPORTED_LANGUAGES: set[str] = {
        "en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur", "ne",
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
        self._daily_limit: int = 200
        if not api_key:
            logger.warning("NewsData.io API key not provided; source will return empty results")

    # --- Async context manager -----------------------------------------------

    async def __aenter__(self) -> NewsDataSource:
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
        """Search NewsData.io and return parsed :class:`ArticleRef` list.

        Never raises -- all HTTP and parse errors are caught, logged, and
        result in an empty list.
        """
        if not self._api_key:
            return []

        if language not in self._SUPPORTED_LANGUAGES:
            logger.debug("NewsData.io does not support language %r; skipping", language)
            return []

        if self._daily_count >= self._daily_limit:
            logger.debug(
                "NewsData.io daily limit reached (%d/%d)",
                self._daily_count,
                self._daily_limit,
            )
            return []

        params = {
            "apikey": self._api_key,
            "q": query,
            "language": language,
            "country": country.lower(),
        }

        try:
            client = self._ensure_client()
            response = await client.get(_BASE_URL, params=params, timeout=self._timeout)
            self._daily_count += 1
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                logger.error(
                    "NewsData.io invalid API key (HTTP 401) for query=%r lang=%s",
                    query,
                    language,
                )
            elif status == 403:
                self._daily_count = self._daily_limit
                logger.warning(
                    "NewsData.io quota exhausted (HTTP 403) for query=%r lang=%s",
                    query,
                    language,
                )
            elif status == 429:
                logger.warning(
                    "NewsData.io rate limited (HTTP 429) for query=%r lang=%s",
                    query,
                    language,
                )
            else:
                logger.warning(
                    "NewsData.io HTTP %s for query=%r lang=%s",
                    status,
                    query,
                    language,
                )
            return []
        except httpx.TimeoutException:
            logger.warning(
                "NewsData.io request timed out for query=%r lang=%s",
                query,
                language,
            )
            return []
        except httpx.RequestError as exc:
            logger.warning(
                "Network error fetching NewsData.io for query=%r lang=%s: %s",
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
                "Failed to parse NewsData.io JSON for query=%r lang=%s",
                query,
                language,
                exc_info=True,
            )
            return []

        # NewsData.io may return HTTP 200 with {"status": "error", ...}.
        if data.get("status") == "error":
            error_msg = data.get("results", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            logger.warning(
                "NewsData.io API error for query=%r lang=%s: %s",
                query,
                language,
                error_msg,
            )
            return []

        results = data.get("results") or []

        articles: list[ArticleRef] = []
        skipped = 0
        for item in results:
            ref = _newsdata_to_ref(item, language, state, search_term)
            if ref is not None:
                articles.append(ref)
            else:
                skipped += 1

        logger.info(
            "NewsData.io query=%r lang=%s: %d articles parsed, %d entries skipped",
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
