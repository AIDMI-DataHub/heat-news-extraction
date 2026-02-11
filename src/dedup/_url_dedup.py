"""URL-based article deduplication.

Normalizes URLs (strips tracking parameters, www prefix, fragments,
trailing slashes; lowercases scheme/host; sorts query params) and
deduplicates articles by normalized URL, keeping the higher-quality version.
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from src.models.article import Article

logger = logging.getLogger(__name__)

# Tracking parameters to strip during URL normalization.
_TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "yclid",
        "msclkid",
        "_ga",
        "_gl",
        "ref",
        "source",
        "mkt_tok",
        "mc_cid",
        "mc_eid",
        "hsCtaTracking",
        "si",
        "__cft__",
        "__tn__",
    }
)


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication comparison.

    - Lowercases scheme and netloc
    - Strips ``www.`` prefix from netloc
    - Strips trailing slash from path (keeps "/" if path is empty)
    - Removes tracking parameters from query string
    - Sorts remaining query parameters for deterministic comparison
    - Removes fragment
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    # Strip tracking params and sort remaining
    params = parse_qs(parsed.query, keep_blank_values=False)
    clean = sorted(
        (k, sorted(v))
        for k, v in params.items()
        if k.lower() not in _TRACKING_PARAMS
    )
    query = urlencode(clean, doseq=True)
    # Remove fragment
    return urlunparse((scheme, netloc, path, "", query, ""))


def _quality_score(article: Article) -> int:
    """Score article data quality for duplicate resolution.

    Higher score = better quality. Used to decide which duplicate to keep.

    Scoring:
    - +100 + len(full_text) if full_text is not None (longer = better extraction)
    - +10 if district is not None (has district-level geo info)
    - +5 if source != "Unknown" (has identified source)
    """
    score = 0
    if article.full_text is not None:
        score += 100 + len(article.full_text)
    if article.district is not None:
        score += 10
    if article.source != "Unknown":
        score += 5
    return score


def deduplicate_by_url(articles: list[Article]) -> list[Article]:
    """Deduplicate articles by normalized URL, keeping the higher-quality version.

    Builds a dict keyed by normalized URL. When a collision occurs,
    the article with the higher ``_quality_score()`` replaces the existing one.
    """
    before = len(articles)
    seen: dict[str, Article] = {}
    for article in articles:
        norm = normalize_url(article.url)
        if norm in seen:
            existing = seen[norm]
            if _quality_score(article) > _quality_score(existing):
                seen[norm] = article
        else:
            seen[norm] = article
    result = list(seen.values())
    logger.info("URL dedup: %d -> %d articles", before, len(result))
    return result
