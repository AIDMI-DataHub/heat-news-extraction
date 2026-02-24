"""Tests for extraction helper functions in src.extraction._extractor."""

from __future__ import annotations

import pytest

from src.extraction._extractor import (
    _clean_text,
    _deduplicate_paragraphs,
    _is_boilerplate,
    _is_non_india,
    _should_skip_url,
)


# ─── _should_skip_url tests ─────────────────────────────────────────


class TestShouldSkipUrl:
    def test_msn_root(self) -> None:
        assert _should_skip_url("https://www.msn.com/en-in/news/article") is True

    def test_msn_subdomain(self) -> None:
        assert _should_skip_url("https://sports.msn.com/story/123") is True

    def test_msn_no_www(self) -> None:
        assert _should_skip_url("https://msn.com/en-in/news") is True

    def test_non_msn_domain(self) -> None:
        assert _should_skip_url("https://www.ndtv.com/article") is False

    def test_msn_like_not_matched(self) -> None:
        """A domain containing 'msn' but not actually msn.com."""
        assert _should_skip_url("https://www.notmsn.com/article") is False

    def test_empty_url(self) -> None:
        assert _should_skip_url("") is False

    def test_malformed_url(self) -> None:
        assert _should_skip_url("not-a-url") is False


# ─── _clean_text tests ──────────────────────────────────────────────


class TestCleanText:
    def test_strips_also_read(self) -> None:
        text = "Article body here.\nAlso Read: Some other article\nMore content."
        result = _clean_text(text)
        assert "Also Read" not in result
        assert "Article body here." in result
        assert "More content." in result

    def test_strips_also_read_hindi(self) -> None:
        text = "कुछ पाठ।\nये भी पढ़ें: कोई अन्य लेख\nऔर सामग्री।"
        result = _clean_text(text)
        assert "ये भी पढ़ें" not in result

    def test_strips_app_promo(self) -> None:
        text = "Article body.\nDownload the app for more updates.\nEnd."
        result = _clean_text(text)
        assert "Download the app" not in result
        assert "Article body." in result

    def test_strips_app_promo_hindi(self) -> None:
        text = "लेख शरीर।\nऐप डाउनलोड करें अभी\nसमाप्त।"
        result = _clean_text(text)
        assert "ऐप डाउनलोड करें" not in result

    def test_strips_breadcrumbs(self) -> None:
        text = " - Home\n - India\n - News\nActual article content starts here."
        result = _clean_text(text)
        assert "- Home" not in result
        assert "Actual article content starts here." in result

    def test_strips_copyright(self) -> None:
        text = "Article body here.\n© 2024 Some News Network. All rights reserved."
        result = _clean_text(text)
        assert "© 2024" not in result
        assert "Article body here." in result

    def test_strips_recommended_block(self) -> None:
        text = (
            "Main article text.\n"
            "Related news\n"
            "Some related article 1\n"
            "Some related article 2\n"
            "Some related article 3"
        )
        result = _clean_text(text)
        assert "Related news" not in result

    def test_collapses_excess_newlines(self) -> None:
        text = "Paragraph one.\n\n\n\n\nParagraph two."
        result = _clean_text(text)
        assert "\n\n\n" not in result
        assert "Paragraph one.\n\nParagraph two." == result

    def test_preserves_normal_article(self) -> None:
        text = "This is a normal article.\n\nWith multiple paragraphs.\n\nAnd no junk."
        result = _clean_text(text)
        assert result == text


# ─── _deduplicate_paragraphs tests ──────────────────────────────────


class TestDeduplicateParagraphs:
    def test_removes_duplicate_paragraph(self) -> None:
        text = "Lead paragraph.\n\nSome content.\n\nLead paragraph."
        result = _deduplicate_paragraphs(text)
        assert result.count("Lead paragraph.") == 1
        assert "Some content." in result

    def test_keeps_unique_paragraphs(self) -> None:
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = _deduplicate_paragraphs(text)
        assert result == text

    def test_case_insensitive_dedup(self) -> None:
        text = "Hello world.\n\nhello world.\n\nAnother paragraph."
        result = _deduplicate_paragraphs(text)
        assert result.lower().count("hello world.") == 1

    def test_removes_triple_repeat(self) -> None:
        text = "Repeated lead.\n\nContent.\n\nRepeated lead.\n\nRepeated lead."
        result = _deduplicate_paragraphs(text)
        assert result.count("Repeated lead.") == 1

    def test_empty_paragraphs_ignored(self) -> None:
        text = "First.\n\n\n\nSecond."
        result = _deduplicate_paragraphs(text)
        assert "First." in result
        assert "Second." in result


# ─── _is_non_india tests ────────────────────────────────────────────


class TestIsNonIndia:
    def test_tennessee_in_title(self) -> None:
        assert _is_non_india(
            "Students faced with extreme heat in college dorms at UT Tennessee",
            "Some article text about heat.",
        ) is True

    def test_california_in_text(self) -> None:
        assert _is_non_india(
            "Extreme heat grips western US",
            "California experienced record temperatures this week in Los Angeles.",
        ) is True

    def test_india_article_passes(self) -> None:
        assert _is_non_india(
            "Heatwave in Rajasthan kills 10",
            "Rajasthan faced severe heatwave conditions with temperatures crossing 48C.",
        ) is False

    def test_indiana_not_matched(self) -> None:
        """Word boundary prevents 'Indiana' from matching inside 'India'."""
        assert _is_non_india(
            "Heatwave conditions in India worsen",
            "India faces severe heat. Indiana is not mentioned as a state.",
        ) is False

    def test_no_text(self) -> None:
        assert _is_non_india("Heatwave in Delhi", None) is False

    def test_new_york_in_title(self) -> None:
        assert _is_non_india("Heat emergency declared in New York", None) is True

    def test_multiple_states_in_text(self) -> None:
        assert _is_non_india(
            "Heat advisory",
            "Texas and Florida both issued heat warnings this week.",
        ) is True


# ─── Expanded boilerplate phrases tests ─────────────────────────────


class TestBoilerplateExpanded:
    def test_copyright_symbol_detected(self) -> None:
        text = "Copyright © 2024 CNN. All rights reserved."
        assert _is_boilerplate(text) is True

    def test_reverse_copyright_detected(self) -> None:
        text = "© Copyright 2024 Some Network."
        assert _is_boilerplate(text) is True

    def test_trademark_detected(self) -> None:
        text = "CNN is a trademark of Turner Broadcasting."
        assert _is_boilerplate(text) is True

    def test_registered_trademark_detected(self) -> None:
        text = "This is a registered trademark notice."
        assert _is_boilerplate(text) is True

    def test_long_text_not_boilerplate(self) -> None:
        text = "Copyright © 2024. " + "x" * 500
        assert _is_boilerplate(text) is False
