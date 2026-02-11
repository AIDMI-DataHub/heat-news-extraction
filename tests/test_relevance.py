"""Tests for relevance scoring and article filtering."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.dedup._relevance import filter_articles, score_relevance
from src.models.article import Article

IST = ZoneInfo("Asia/Kolkata")


def _make_article(**overrides) -> Article:
    """Create an Article with sensible defaults for relevance testing."""
    defaults = {
        "title": "Test article",
        "url": "https://example.com/1",
        "source": "Test",
        "date": datetime(2024, 6, 1, tzinfo=IST),
        "language": "en",
        "state": "Rajasthan",
        "search_term": "heatwave",
        "full_text": None,
        "relevance_score": 0.0,
    }
    defaults.update(overrides)
    return Article(**defaults)


# ─── score_relevance tests ──────────────────────────────────────────────


class TestScoreRelevance:
    def test_scores_article_with_multiple_heat_terms(self) -> None:
        """Article mentioning multiple heat terms scores > 0.5."""
        article = _make_article(
            title="Heatwave causes heat stroke in Rajasthan",
            full_text="Severe heatwave conditions led to heat stroke cases. Temperature soared to 48 degrees.",
        )
        score = score_relevance(article)
        assert score > 0.5

    def test_scores_zero_for_no_heat_terms(self) -> None:
        """Article about cricket with no heat terms scores 0.0."""
        article = _make_article(
            title="India cricket match in Mumbai",
            full_text="India won the cricket match against Australia by 5 wickets in a thrilling encounter.",
        )
        score = score_relevance(article)
        assert score == 0.0

    def test_title_bonus_increases_score(self) -> None:
        """Article with heat terms in title scores higher than same terms only in body."""
        article_title = _make_article(
            title="Heatwave alert in Delhi",
            full_text="Officials issued warnings today.",
        )
        article_body = _make_article(
            title="Officials issue warnings today",
            full_text="Heatwave alert conditions prevail in Delhi.",
        )
        score_with_title = score_relevance(article_title)
        score_body_only = score_relevance(article_body)
        assert score_with_title > score_body_only

    def test_full_text_none_with_heat_title_scores_above_zero(self) -> None:
        """Article with full_text=None but heat terms in title scores >= 0.3."""
        article = _make_article(
            title="Severe heatwave grips north India",
            full_text=None,
        )
        score = score_relevance(article)
        assert score >= 0.3

    def test_category_diversity_bonus(self) -> None:
        """Article matching 2+ categories scores higher than one matching only 1."""
        # Single category: weather only
        article_one_cat = _make_article(
            title="Heatwave in Rajasthan",
            full_text="Heatwave conditions continue with heat wave warnings.",
        )
        # Multiple categories: weather + health + temperature
        article_multi_cat = _make_article(
            title="Heatwave in Rajasthan",
            full_text="Heatwave conditions led to heat stroke cases. Mercury soars past 47 degrees.",
        )
        score_one = score_relevance(article_one_cat)
        score_multi = score_relevance(article_multi_cat)
        assert score_multi > score_one


# ─── filter_articles tests ──────────────────────────────────────────────


class TestFilterArticles:
    def test_keeps_high_score_article(self) -> None:
        """Article with heatwave content is kept."""
        article = _make_article(
            title="Severe heatwave kills 10 in Rajasthan",
            full_text="Heatwave conditions and heat stroke deaths reported. Temperature crossed 48 degrees.",
        )
        result = filter_articles([article])
        assert len(result) == 1

    def test_excludes_cricket_score_article(self) -> None:
        """Article about cricket scores with no heat terms is excluded."""
        article = _make_article(
            title="India cricket score 350 runs in test match",
            full_text="India posted a score of 350 runs with 8 wickets in hand in the cricket test match.",
        )
        result = filter_articles([article])
        assert len(result) == 0

    def test_keeps_borderline_article(self) -> None:
        """Article with low score but no exclusion pattern match is KEPT (high recall)."""
        article = _make_article(
            title="Summer conditions in Delhi",
            full_text="Warm weather persists across the capital region today.",
        )
        # This article has no heat terms (score ~0) but also doesn't match
        # any exclusion pattern, so high-recall filter keeps it
        result = filter_articles([article])
        # If score is 0 and no exclusion match: kept (score >= 0.05 is false,
        # but not matching exclusion means it passes the OR condition)
        # Actually per logic: exclude ONLY if score < 0.05 AND matches exclusion
        # So if score < 0.05 and NOT matching exclusion: KEPT
        assert len(result) == 1

    def test_keeps_article_with_heat_and_cricket(self) -> None:
        """Article mentioning both heatwave and cricket is KEPT."""
        article = _make_article(
            title="Cricket match suspended due to heatwave",
            full_text="The cricket match was suspended after players suffered heat stroke due to extreme heatwave conditions.",
        )
        result = filter_articles([article])
        assert len(result) == 1

    def test_updates_relevance_score(self) -> None:
        """After filtering, each article has its relevance_score updated from 0.0."""
        article = _make_article(
            title="Heatwave alert issued for Rajasthan",
            full_text="IMD issued heatwave alert. Temperature expected to cross 45 degrees.",
            relevance_score=0.0,
        )
        result = filter_articles([article])
        assert len(result) == 1
        assert result[0].relevance_score > 0.0
