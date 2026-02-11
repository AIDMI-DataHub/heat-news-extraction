"""Trafilatura-based article extraction with async bridge and batch processing.

Provides :func:`extract_article` (single) and :func:`extract_articles` (batch)
for converting :class:`~src.models.article.ArticleRef` objects into
:class:`~src.models.article.Article` objects with ``full_text`` populated.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import trafilatura

from src.extraction._resolver import resolve_url
from src.models.article import Article, ArticleRef

logger = logging.getLogger(__name__)


async def _fetch_html(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch the HTML content of *url*.

    Uses ``follow_redirects=True`` and a 15-second timeout (5-second
    connect).  Returns the decoded HTML string on success, or ``None``
    on any failure.  Never raises.
    """
    try:
        response = await client.get(
            url,
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        response.raise_for_status()
        return response.text
    except httpx.TimeoutException:
        logger.warning("Timeout fetching %s", url)
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %s fetching %s", exc.response.status_code, url)
        return None
    except Exception:
        logger.error("Unexpected error fetching %s", url, exc_info=True)
        return None


async def _extract_text(html: str, url: str) -> str | None:
    """Extract article text from *html* using trafilatura.

    Runs the synchronous ``trafilatura.extract()`` in a thread via
    :func:`asyncio.to_thread` so the event loop is not blocked.
    Returns the extracted text string, or ``None`` on failure.
    """
    try:
        text: str | None = await asyncio.to_thread(
            trafilatura.extract,
            html,
            favor_recall=True,
            include_comments=False,
            include_tables=True,
            deduplicate=True,
            url=url,
        )
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
    refs: list[ArticleRef], max_concurrent: int = 10
) -> list[Article]:
    """Batch-extract articles from a list of :class:`ArticleRef`.

    Creates a shared :class:`httpx.AsyncClient` and uses an
    :class:`asyncio.Semaphore` to bound concurrency at *max_concurrent*.

    This is the public batch API consumed by the pipeline.

    Parameters
    ----------
    refs:
        Article references collected by the query engine.
    max_concurrent:
        Maximum number of concurrent extraction tasks.

    Returns
    -------
    list[Article]
        One :class:`Article` per input ref (order preserved).
    """
    if not refs:
        logger.info("No article refs to extract")
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _extract_one(ref: ArticleRef) -> Article:
        async with semaphore:
            return await extract_article(ref, client)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(15.0, connect=5.0),
    ) as client:
        tasks = [_extract_one(ref) for ref in refs]
        articles: list[Article] = await asyncio.gather(
            *tasks, return_exceptions=False
        )

    # Log batch summary
    successful = sum(1 for a in articles if a.full_text is not None)
    failed = len(articles) - successful
    logger.info(
        "Extraction complete: %d refs, %d extracted, %d failed",
        len(refs),
        successful,
        failed,
    )

    return articles
