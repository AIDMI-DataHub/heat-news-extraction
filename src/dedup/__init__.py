"""Deduplication and relevance filtering pipeline for heat-related news articles.

Provides URL-based deduplication, title similarity deduplication, relevance
scoring, and configurable exclusion filtering. The main entry point is
``deduplicate_and_filter()`` which composes all stages into a single pipeline.

Pipeline stages (in order):
    1. URL dedup -- remove articles with identical normalized URLs
    2. Title dedup -- remove articles with similar titles within language buckets
    3. Relevance scoring + filtering -- score each article and exclude irrelevant ones
"""

from __future__ import annotations

import logging

from src.dedup._relevance import filter_articles, score_relevance
from src.dedup._title_dedup import deduplicate_by_title
from src.dedup._url_dedup import deduplicate_by_url, normalize_url
from src.models.article import Article

logger = logging.getLogger(__name__)

__all__ = [
    "deduplicate_and_filter",
    "deduplicate_by_url",
    "deduplicate_by_title",
    "normalize_url",
    "score_relevance",
    "filter_articles",
]


def deduplicate_and_filter(articles: list[Article]) -> list[Article]:
    """Run the full deduplication and filtering pipeline.

    Composes all pipeline stages in order:
        1. URL dedup -- removes articles with identical normalized URLs
        2. Title dedup -- removes similar titles within same-language buckets
        3. Score + filter -- scores relevance and excludes clearly irrelevant articles

    Args:
        articles: Raw list of articles from extraction.

    Returns:
        Deduplicated, scored, and filtered list of articles.
    """
    input_count = len(articles)

    # Stage 1: URL deduplication
    deduped_url = deduplicate_by_url(articles)

    # Stage 2: Title deduplication
    deduped_title = deduplicate_by_title(deduped_url, threshold=0.85)

    # Stage 3: Relevance scoring + filtering
    filtered = filter_articles(deduped_title)

    logger.info(
        "Dedup+filter pipeline: %d -> %d articles",
        input_count,
        len(filtered),
    )
    return filtered
