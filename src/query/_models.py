"""Query data models and query string construction helpers.

Provides frozen dataclasses for query representation (Query, QueryResult)
and standalone helper functions for building API-ready query strings with
proper OR-combining, quoting, and character-limit handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.models.article import ArticleRef


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Query:
    """A single search query ready for execution against a news source.

    Attributes:
        query_string: The actual search text ready for the API.
        language: ISO 639-1 language code.
        state: State/UT name (human-readable).
        state_slug: Kebab-case identifier for result tracking.
        level: Whether this targets a state or its districts.
        category: Heat term category (for Google News category queries, None for broad).
        source_hint: Which news source this query is designed for.
        districts: District names if level == "district".
    """

    query_string: str
    language: str
    state: str
    state_slug: str
    level: Literal["state", "district"]
    category: str | None
    source_hint: Literal["google", "newsdata", "gnews"]
    districts: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryResult:
    """Result of executing a query against one news source.

    Attributes:
        query: The original Query that was executed.
        source_name: Name of the source that produced these results.
        articles: List of article references found.
        success: Whether the query executed without error.
        error: Error description if success is False, None otherwise.
    """

    query: Query
    source_name: str
    articles: list[ArticleRef]
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Query string construction helpers
# ---------------------------------------------------------------------------
def _quote_if_multi_word(term: str) -> str:
    """Wrap a term in double quotes if it contains spaces."""
    if " " in term:
        return f'"{term}"'
    return term


def build_category_query(terms: list[str], location: str) -> str:
    """Build a category-based query: (term1 OR "multi word" OR term3) location.

    Combines all terms with OR inside parentheses, then appends the location
    name. Multi-word terms are double-quoted to prevent OR from splitting them.

    Args:
        terms: List of search terms (e.g. ["heatwave", "heat stroke", "loo"]).
        location: Geographic location name (e.g. "Rajasthan").

    Returns:
        Query string like ``(heatwave OR "heat stroke" OR loo) Rajasthan``.
    """
    if not terms:
        return location
    quoted = [_quote_if_multi_word(t) for t in terms]
    terms_part = " OR ".join(quoted)
    return f"({terms_part}) {location}"


def build_broad_query(terms: list[str], location: str, max_chars: int) -> str:
    """Build a broad query that fits within a character limit.

    Picks the highest-priority terms (terms are assumed priority-ordered,
    most important first) that fit within *max_chars*. Multi-word terms are
    double-quoted.

    Args:
        terms: Priority-ordered list of search terms.
        location: Geographic location name.
        max_chars: Maximum allowed length for the full query string.

    Returns:
        Query string like ``(heatwave OR "heat stroke") Rajasthan``.
    """
    if not terms:
        return location
    # Overhead: "(" + terms_part + ") " + location
    overhead = len(location) + 3  # space + opening paren + closing paren
    budget = max_chars - overhead
    selected: list[str] = []
    used = 0
    for t in terms:
        term_repr = _quote_if_multi_word(t)
        # Cost: the term itself plus " OR " separator (if not first)
        cost = len(term_repr) + (4 if selected else 0)
        if used + cost > budget:
            break
        selected.append(term_repr)
        used += cost
    if not selected:
        # Last resort: truncate the first term to fit
        selected = [terms[0][: max(1, budget)]]
    terms_part = " OR ".join(selected)
    return f"({terms_part}) {location}"


def batch_districts(
    districts: list[str], heat_term: str, max_chars: int
) -> list[str]:
    """Batch district names into query strings within a character limit.

    Each batch produces a query string of the form:
    ``heat_term ("District1" OR "District2" OR District3)``

    Multi-word district names are double-quoted.

    Args:
        districts: List of district name strings.
        heat_term: The heat term to prepend (e.g. "heatwave").
        max_chars: Maximum allowed length for each query string.

    Returns:
        List of query strings, each within *max_chars*.
    """
    if not districts:
        return []

    # Overhead: heat_term + " (" + district_part + ")"
    overhead = len(heat_term) + 3  # " (" prefix + ")" suffix
    budget = max_chars - overhead

    queries: list[str] = []
    batch: list[str] = []
    used = 0

    for d in districts:
        name = _quote_if_multi_word(d)
        cost = len(name) + (4 if batch else 0)  # " OR " separator
        if used + cost > budget and batch:
            # Flush current batch
            query = f'{heat_term} ({" OR ".join(batch)})'
            queries.append(query)
            batch = [name]
            used = len(name)
        else:
            batch.append(name)
            used += cost

    if batch:
        query = f'{heat_term} ({" OR ".join(batch)})'
        queries.append(query)

    return queries
