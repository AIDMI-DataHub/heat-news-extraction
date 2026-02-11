"""Relevance scoring and filtering for heat-related news articles.

Scores each article based on heat term presence, category diversity, and
title bonus. Filters out clearly irrelevant articles using configurable
exclusion patterns (loaded from exclusion_patterns.json).

High-recall design: articles are only excluded if they score below 0.05
AND match an exclusion pattern. Borderline articles are kept.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from src.data.heat_terms_loader import TERM_CATEGORIES, get_terms_by_category
from src.models.article import Article

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_exclusion_patterns() -> list[re.Pattern[str]]:
    """Load and compile exclusion patterns from JSON config file.

    Cached: only reads disk once per process.

    Returns:
        List of compiled regex patterns for exclusion matching.
    """
    data_path = (
        Path(__file__).resolve().parent.parent / "data" / "exclusion_patterns.json"
    )
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return [
        re.compile(entry["pattern"], re.IGNORECASE)
        for entry in raw["patterns"]
    ]


def _combine_text(article: Article) -> str:
    """Combine article title and full_text into a single lowercase string.

    Args:
        article: Article to extract text from.

    Returns:
        Lowercase combined text, or empty string if both are empty/None.
    """
    parts: list[str] = []
    if article.title:
        parts.append(article.title)
    if article.full_text is not None:
        parts.append(article.full_text)
    return "\n".join(parts).lower()


def _matches_exclusion(text: str, patterns: list[re.Pattern[str]]) -> bool:
    """Check if text matches any exclusion pattern.

    Args:
        text: Combined lowercase text to check.
        patterns: List of compiled exclusion regex patterns.

    Returns:
        True if any pattern matches (article is likely irrelevant).
    """
    return any(pattern.search(text) for pattern in patterns)


def score_relevance(article: Article) -> float:
    """Score an article's relevance to heat-related news.

    Scoring formula:
    - term_score: min(matched_terms / 3, 1.0) -- 3+ terms = full score
    - category_score: min(matched_categories / 2, 1.0) -- 2+ categories = full
    - title_bonus: 0.2 if any matched terms appear in title
    - raw_score = (term_score * 0.5) + (category_score * 0.3) + title_bonus

    Special case: if full_text is None but title has heat terms,
    a floor of 0.3 is applied (not penalized for extraction failure).

    Args:
        article: Article to score.

    Returns:
        Relevance score between 0.0 and 1.0.
    """
    text = _combine_text(article)
    if not text:
        return 0.0

    matched_terms: set[str] = set()
    matched_categories: set[str] = set()

    for category in sorted(TERM_CATEGORIES):
        terms = get_terms_by_category("en", category)
        for term in terms:
            if term.lower() in text:
                matched_terms.add(term.lower())
                matched_categories.add(category)

    if not matched_terms:
        return 0.0

    term_score = min(len(matched_terms) / 3.0, 1.0)
    category_score = min(len(matched_categories) / 2.0, 1.0)

    title_lower = article.title.lower()
    title_terms = sum(1 for t in matched_terms if t in title_lower)
    title_bonus = 0.2 if title_terms > 0 else 0.0

    raw_score = (term_score * 0.5) + (category_score * 0.3) + title_bonus

    # Special case: full_text=None with heat terms in title gets floor of 0.3
    if article.full_text is None and title_terms > 0:
        raw_score = max(raw_score, 0.3)

    return min(raw_score, 1.0)


def filter_articles(articles: list[Article]) -> list[Article]:
    """Score and filter articles for relevance to heat-related news.

    High-recall filter: excludes ONLY if relevance_score < 0.05 AND the
    article matches an exclusion pattern. Borderline articles are kept.

    Each article gets its relevance_score updated via model_copy.

    Args:
        articles: List of articles to score and filter.

    Returns:
        List of scored and filtered articles.
    """
    before = len(articles)
    patterns = _load_exclusion_patterns()
    result: list[Article] = []

    for article in articles:
        score = score_relevance(article)
        scored = article.model_copy(update={"relevance_score": score})

        # High-recall: exclude ONLY if score < 0.05 AND matches exclusion
        if score < 0.05:
            text = _combine_text(article)
            if _matches_exclusion(text, patterns):
                continue  # Excluded: low score AND matches exclusion pattern

        result.append(scored)

    after = len(result)
    logger.info("Relevance filter: %d -> %d articles (excluded %d)", before, after, before - after)
    return result
