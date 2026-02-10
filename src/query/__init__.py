"""Query generation engine for the heat news extraction pipeline.

Provides data models for search queries, query string construction helpers,
and a QueryGenerator that combines heat terms with geographic data to produce
API-ready query strings for all three news sources.
"""

from ._generator import GNEWS_SUPPORTED_LANGUAGES, QueryGenerator
from ._models import (
    Query,
    QueryResult,
    batch_districts,
    build_broad_query,
    build_category_query,
)

__all__ = [
    "GNEWS_SUPPORTED_LANGUAGES",
    "Query",
    "QueryGenerator",
    "QueryResult",
    "batch_districts",
    "build_broad_query",
    "build_category_query",
]
