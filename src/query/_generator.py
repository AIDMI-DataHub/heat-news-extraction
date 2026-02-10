"""QueryGenerator -- combines heat terms with geographic data to produce queries.

Generates API-ready search queries for all three news sources (Google News,
NewsData.io, GNews) at both state and district levels. Each source gets a
different query strategy:

- Google News: 8 category-based OR-combined queries per state-language pair
- NewsData.io: 1 broad query per state-language pair (512 char limit)
- GNews: 1 broad query per state-language pair (200 char limit, 8 languages only)
"""

from __future__ import annotations

from typing import Literal

from src.data.geo_loader import StateUT
from src.data.heat_terms_loader import (
    TERM_CATEGORIES,
    get_terms_by_category,
    get_terms_for_language,
)

from ._models import Query, batch_districts, build_broad_query, build_category_query

# Languages supported by GNews API (mirrors GNewsSource._SUPPORTED_LANGUAGES
# but defined here to avoid circular imports from src.sources).
GNEWS_SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {"en", "hi", "bn", "ta", "te", "mr", "ml", "pa"}
)

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
            for lang in region.languages:
                # --- Google News: one query per category ---
                for cat in sorted(TERM_CATEGORIES):
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

                # --- NewsData.io: one broad query per state-language pair ---
                all_terms = get_terms_for_language(lang)
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

                # --- GNews: one broad query per state-language pair (8 langs only) ---
                if lang in GNEWS_SUPPORTED_LANGUAGES:
                    all_terms = get_terms_for_language(lang)
                    if all_terms:
                        query_string = build_broad_query(
                            all_terms, region.name, 200
                        )
                        gnews_queries.append(
                            Query(
                                query_string=query_string,
                                language=lang,
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

            for lang in region.languages:
                # Skip unsupported languages for GNews
                if source_hint == "gnews" and lang not in GNEWS_SUPPORTED_LANGUAGES:
                    continue

                # Pick the best heat term for district batching:
                # prefer "heatwave" category terms, fall back to first available
                heatwave_terms = get_terms_by_category(lang, "heatwave")
                if heatwave_terms:
                    heat_term = heatwave_terms[0]
                else:
                    all_terms = get_terms_for_language(lang)
                    heat_term = all_terms[0] if all_terms else "heatwave"

                # Batch districts into queries within char limit
                batched_queries = batch_districts(
                    district_names, heat_term, max_chars
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
