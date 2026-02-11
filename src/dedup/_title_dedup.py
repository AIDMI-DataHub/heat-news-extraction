"""Title-based article deduplication with language bucketing.

Compares article titles using difflib.SequenceMatcher within same-language
buckets. Strips source name suffixes (e.g., " - NDTV") before comparison.
When duplicates are found, the higher-quality version is kept.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from difflib import SequenceMatcher

from src.dedup._url_dedup import _quality_score
from src.models.article import Article

logger = logging.getLogger(__name__)


def _strip_source_suffix(title: str) -> str:
    """Strip trailing source name suffix from a title.

    Many news aggregators format titles as "Headline - Source Name".
    This strips the " - Source Name" part if the suffix is short enough
    to be a source name (<= 40 characters).

    Examples:
        "Heatwave kills 10 - Times of India" -> "Heatwave kills 10"
        "Heatwave in Delhi" -> "Heatwave in Delhi" (no suffix)
    """
    idx = title.rfind(" - ")
    if idx == -1:
        return title
    suffix = title[idx + 3 :]
    if len(suffix) <= 40:
        return title[:idx]
    return title


def _title_similarity(title_a: str, title_b: str) -> float:
    """Compute similarity ratio between two titles.

    Strips source suffixes, lowercases, and strips whitespace before
    comparison. Works with any Unicode script (Latin, Devanagari, Tamil,
    etc.) because SequenceMatcher operates on Unicode code points.
    """
    a = _strip_source_suffix(title_a).strip().lower()
    b = _strip_source_suffix(title_b).strip().lower()
    return SequenceMatcher(None, a, b).ratio()


def deduplicate_by_title(
    articles: list[Article],
    threshold: float = 0.85,
) -> list[Article]:
    """Deduplicate articles by title similarity within same-language buckets.

    Groups articles by language, then within each group uses pairwise
    SequenceMatcher comparison. When similarity >= threshold, the article
    with the higher ``_quality_score()`` is kept.

    Args:
        articles: List of articles to deduplicate.
        threshold: Minimum similarity ratio to consider as duplicate (default 0.85).

    Returns:
        Deduplicated list of articles.
    """
    before = len(articles)

    # Bucket by language
    buckets: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        buckets[article.language].append(article)

    # Deduplicate within each language bucket
    result: list[Article] = []
    for _lang, lang_articles in buckets.items():
        kept: list[Article] = []
        for article in lang_articles:
            is_dup = False
            for i, existing in enumerate(kept):
                if _title_similarity(article.title, existing.title) >= threshold:
                    # Duplicate found -- keep the higher-quality version
                    if _quality_score(article) > _quality_score(existing):
                        kept[i] = article
                    is_dup = True
                    break
            if not is_dup:
                kept.append(article)
        result.extend(kept)

    logger.info("Title dedup: %d -> %d articles", before, len(result))
    return result
