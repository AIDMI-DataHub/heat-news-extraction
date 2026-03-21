"""QueryGenerator -- combines heat terms with geographic data to produce queries.

Generates API-ready search queries for all three news sources (Google News,
NewsData.io, GNews) at both state and district levels. Each source gets a
different query strategy:

- Google News: 4 category-based OR-combined queries + 2 phrase queries per
  state-language pair. Categories: weather, health, temperature, governance.
  Phrase queries use exact-match for the top weather and health terms
  (e.g. ``"heatwave" Rajasthan``), catching articles the OR-chains miss.
- NewsData.io: 1 broad query per state-language pair (512 char limit),
  using only terms from core categories
- GNews: 1 broad query per state-language pair (200 char limit). Falls
  back to English for unsupported languages (gu, kn, or, ur, as, ne).
"""

from __future__ import annotations

from typing import Literal

from src.data.geo_loader import StateUT
from src.data.heat_terms_loader import (
    get_terms_by_category,
    get_terms_for_language,
)

from ._models import Query, batch_districts, build_broad_query, build_category_query


def _query_languages(region: StateUT) -> list[str]:
    """Return query languages: primary regional language + English.

    Uses only two languages per state to reduce query count while
    ensuring every state is searched in both its main regional
    language and English for broader coverage.
    """
    primary = next((lang for lang in region.languages if lang != "en"), None)
    if primary:
        return [primary, "en"]
    return ["en"]

# Languages supported by GNews API (mirrors GNewsSource._SUPPORTED_LANGUAGES
# but defined here to avoid circular imports from src.sources).
GNEWS_SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {"en", "hi", "bn", "ta", "te", "mr", "ml", "pa"}
)

# Query with categories that are heat-specific or contain IMD/alert terms
# that frequently appear in heat news articles. Generic categories (power,
# education, labor, agriculture, urban_infra) are excluded because they
# match too many irrelevant articles (e.g. "school closed" matches festival
# closures). Governance is included because its terms (IMD warning, red
# alert, heat advisory) are strong heat-news signals.
QUERY_CATEGORIES: tuple[str, ...] = ("weather", "health", "temperature", "governance")

# Character limits per source for query strings.
_CHAR_LIMITS: dict[str, int] = {
    "google": 2000,
    "newsdata": 512,
    "gnews": 200,
}


class QueryGenerator:
    """Generates search queries from geographic data and heat terms.

    Constructor takes no arguments -- loads data from geo_loader and
    heat_terms_loader internally via their cached loaders.
    """

    def generate_state_queries(
        self, regions: list[StateUT]
    ) -> dict[str, list[Query]]:
        """Generate state-level queries for all three sources.

        For each region and each of its languages:
        - Google News: one Query per category (8 categories from TERM_CATEGORIES)
        - NewsData.io: one broad Query per state-language pair (512 char limit)
        - GNews: one broad Query per state-language pair (200 char limit),
          only for languages in GNEWS_SUPPORTED_LANGUAGES

        Args:
            regions: List of StateUT objects to generate queries for.

        Returns:
            Dict keyed by source_hint ("google", "newsdata", "gnews"),
            each containing a list of Query objects.
        """
        google_queries: list[Query] = []
        newsdata_queries: list[Query] = []
        gnews_queries: list[Query] = []

        for region in regions:
            for lang in _query_languages(region):
                # --- Google News: one query per core category ---
                for cat in QUERY_CATEGORIES:
                    terms = get_terms_by_category(lang, cat)
                    if not terms:
                        continue
                    query_string = build_category_query(terms, region.name)
                    google_queries.append(
                        Query(
                            query_string=query_string,
                            language=lang,
                            state=region.name,
                            state_slug=region.slug,
                            level="state",
                            category=cat,
                            source_hint="google",
                        )
                    )

                # --- Google News: phrase queries for top terms ---
                # Exact-match phrase queries (e.g. "heatwave" Rajasthan)
                # catch articles that OR-chain queries miss. Mirrors the
                # monsoon pipeline's approach of using individual high-impact
                # terms for precision.
                for phrase_cat in ("weather", "health"):
                    phrase_terms = get_terms_by_category(lang, phrase_cat)
                    if phrase_terms:
                        # Use the first (highest-priority) term as an exact phrase
                        phrase = phrase_terms[0]
                        query_string = f'"{phrase}" {region.name}'
                        google_queries.append(
                            Query(
                                query_string=query_string,
                                language=lang,
                                state=region.name,
                                state_slug=region.slug,
                                level="state",
                                category=f"{phrase_cat}_phrase",
                                source_hint="google",
                            )
                        )

                # --- NewsData.io: one broad query per state-language pair ---
                # Only use terms from core categories to avoid generic matches.
                all_terms = _get_core_terms(lang)
                if all_terms:
                    query_string = build_broad_query(all_terms, region.name, 512)
                    newsdata_queries.append(
                        Query(
                            query_string=query_string,
                            language=lang,
                            state=region.name,
                            state_slug=region.slug,
                            level="state",
                            category=None,
                            source_hint="newsdata",
                        )
                    )

                # --- GNews: one broad query per state-language pair ---
                # GNews supports 8 languages natively; for unsupported
                # languages the source adapter falls back to English.
                gnews_lang = lang if lang in GNEWS_SUPPORTED_LANGUAGES else "en"
                all_terms = _get_core_terms(gnews_lang)
                if all_terms:
                    query_string = build_broad_query(
                        all_terms, region.name, 200
                    )
                    gnews_queries.append(
                        Query(
                            query_string=query_string,
                            language=gnews_lang,
                            state=region.name,
                            state_slug=region.slug,
                            level="state",
                            category=None,
                            source_hint="gnews",
                        )
                    )

        return {
            "google": google_queries,
            "newsdata": newsdata_queries,
            "gnews": gnews_queries,
        }

    def generate_district_queries(
        self,
        regions: list[StateUT],
        source_hint: Literal["google", "newsdata", "gnews"] = "google",
    ) -> list[Query]:
        """Generate district-level queries for the given regions.

        For each region and each of its languages, batches district names
        into query strings within the source's character limit. Uses the
        first "heatwave" category term as the primary heat term for district
        batching (falls back to the first term from get_terms_for_language
        if no heatwave terms exist).

        Args:
            regions: List of StateUT objects to generate district queries for.
            source_hint: Which source these queries target. Determines the
                character limit (google=2000, newsdata=512, gnews=200).

        Returns:
            List of Query objects with level="district".
        """
        max_chars = _CHAR_LIMITS.get(source_hint, 2000)
        queries: list[Query] = []

        for region in regions:
            if not region.districts:
                continue
            district_names = [d.name for d in region.districts]

            for lang in _query_languages(region):
                # Skip unsupported languages for GNews
                if source_hint == "gnews" and lang not in GNEWS_SUPPORTED_LANGUAGES:
                    continue

                # Pick the best heat term for district batching:
                # prefer "weather" category terms, fall back to first available
                heatwave_terms = get_terms_by_category(lang, "weather")
                if heatwave_terms:
                    heat_term = heatwave_terms[0]
                else:
                    all_terms = get_terms_for_language(lang)
                    heat_term = all_terms[0] if all_terms else "heatwave"

                # Batch districts into queries within char limit
                batched_queries = batch_districts(
                    district_names, heat_term, max_chars,
                    state_name=region.name,
                )

                for bq in batched_queries:
                    # Extract which districts are in this batch by parsing
                    # the query string (between parentheses, OR-separated).
                    # More reliable: compute batch membership directly.
                    batch_districts_in_query = _extract_batch_districts(
                        bq, heat_term, district_names
                    )
                    queries.append(
                        Query(
                            query_string=bq,
                            language=lang,
                            state=region.name,
                            state_slug=region.slug,
                            level="district",
                            category=None,
                            source_hint=source_hint,
                            districts=tuple(batch_districts_in_query),
                        )
                    )

        return queries


def _get_core_terms(lang: str) -> list[str]:
    """Return heat terms only from the core query categories for a language.

    Used by NewsData.io and GNews broad queries to avoid including generic
    terms (power cuts, school closures, etc.) that cause false positives.
    """
    terms: list[str] = []
    for cat in QUERY_CATEGORIES:
        terms.extend(get_terms_by_category(lang, cat))
    return terms


def _extract_batch_districts(
    query_string: str, heat_term: str, all_districts: list[str]
) -> list[str]:
    """Extract which district names from all_districts appear in a batch query.

    Matches by checking if each district name (or its quoted form) appears
    in the query string. This is used to populate the Query.districts tuple.

    Args:
        query_string: The batched query string produced by batch_districts().
        heat_term: The heat term prefix (used to strip it from the string).
        all_districts: Full list of district names to check against.

    Returns:
        List of district names found in this batch query.
    """
    # The part after the heat_term is the district portion
    found: list[str] = []
    for d in all_districts:
        # Check for quoted or unquoted form
        if f'"{d}"' in query_string or f" {d}" in query_string or query_string.startswith(d):
            # More precise: check within the parenthesized part
            paren_start = query_string.find("(")
            paren_end = query_string.rfind(")")
            if paren_start >= 0 and paren_end > paren_start:
                paren_content = query_string[paren_start + 1 : paren_end]
                if f'"{d}"' in paren_content or d in paren_content.split(" OR "):
                    found.append(d)
    return found
