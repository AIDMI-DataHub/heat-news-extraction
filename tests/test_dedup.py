"""Tests for URL-based and title-based article deduplication."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.dedup._url_dedup import deduplicate_by_url, normalize_url
from src.models.article import Article

IST = ZoneInfo("Asia/Kolkata")


def _make_article(**overrides) -> Article:
    """Create an Article with sensible defaults for dedup testing."""
    defaults = {
        "title": "Heatwave in Rajasthan",
        "url": "https://example.com/article",
        "source": "TestSource",
        "date": datetime(2024, 6, 1, tzinfo=IST),
        "language": "en",
        "state": "Rajasthan",
        "search_term": "heatwave",
    }
    defaults.update(overrides)
    return Article(**defaults)


# ─── normalize_url tests ──────────────────────────────────────────────


class TestNormalizeUrl:
    def test_strips_utm_params(self) -> None:
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_strips_www_prefix(self) -> None:
        url = "https://www.example.com/article"
        result = normalize_url(url)
        assert "www." not in result
        assert "example.com" in result

    def test_lowercase_scheme_and_host(self) -> None:
        url = "HTTP://Example.COM/Path"
        result = normalize_url(url)
        assert result.startswith("http://example.com/")
        # Path case is preserved
        assert "/Path" in result

    def test_strips_trailing_slash(self) -> None:
        url = "https://example.com/path/"
        result = normalize_url(url)
        assert result.endswith("/path")

    def test_strips_fragment(self) -> None:
        url = "https://example.com/article#section"
        result = normalize_url(url)
        assert "#" not in result
        assert "section" not in result

    def test_sorts_remaining_params(self) -> None:
        url = "https://example.com/article?b=2&a=1"
        result = normalize_url(url)
        # a=1 should come before b=2
        a_pos = result.index("a=1")
        b_pos = result.index("b=2")
        assert a_pos < b_pos

    def test_preserves_non_tracking_params(self) -> None:
        url = "https://example.com/article?id=123&utm_source=twitter&page=2"
        result = normalize_url(url)
        assert "id=123" in result
        assert "page=2" in result
        assert "utm_source" not in result


# ─── deduplicate_by_url tests ──────────────────────────────────────────


class TestDeduplicateByUrl:
    def test_removes_exact_url_duplicates(self) -> None:
        a1 = _make_article(
            title="Article A",
            url="https://example.com/same",
            full_text="Short text",
        )
        a2 = _make_article(
            title="Article B",
            url="https://example.com/same",
            full_text="This is a much longer full text for the article",
        )
        result = deduplicate_by_url([a1, a2])
        assert len(result) == 1
        # Longer text should win
        assert result[0].full_text == "This is a much longer full text for the article"

    def test_removes_tracking_param_duplicates(self) -> None:
        a1 = _make_article(
            url="https://example.com/article?utm_source=twitter",
            full_text="Full text here",
        )
        a2 = _make_article(
            url="https://example.com/article?utm_source=facebook",
            full_text="Full text here too",
        )
        result = deduplicate_by_url([a1, a2])
        assert len(result) == 1

    def test_keeps_different_urls(self) -> None:
        a1 = _make_article(url="https://example.com/article-one")
        a2 = _make_article(url="https://example.com/article-two")
        result = deduplicate_by_url([a1, a2])
        assert len(result) == 2

    def test_keeps_higher_quality_with_full_text(self) -> None:
        a1 = _make_article(url="https://example.com/same", full_text=None)
        a2 = _make_article(url="https://example.com/same", full_text="Some text")
        result = deduplicate_by_url([a1, a2])
        assert len(result) == 1
        assert result[0].full_text == "Some text"

    def test_keeps_higher_quality_with_longer_text(self) -> None:
        a1 = _make_article(
            url="https://example.com/same",
            full_text="Short",
        )
        a2 = _make_article(
            url="https://example.com/same",
            full_text="This is significantly longer text content",
        )
        result = deduplicate_by_url([a1, a2])
        assert len(result) == 1
        assert result[0].full_text == "This is significantly longer text content"
