"""Query generation engine for the heat news extraction pipeline.

Provides data models for search queries, query string construction helpers,
a QueryGenerator that combines heat terms with geographic data to produce
API-ready query strings for all three news sources, and rate-limit-aware
SourceScheduler wrappers with per-source factory functions.
"""

from ._generator import GNEWS_SUPPORTED_LANGUAGES, QueryGenerator
from ._models import (
    Query,
    QueryResult,
    batch_districts,
    build_broad_query,
    build_category_query,
)
from ._scheduler import (
    PerSecondLimiter,
    SourceScheduler,
    WindowLimiter,
    create_gnews_scheduler,
    create_google_scheduler,
    create_newsdata_scheduler,
)

__all__ = [
    "GNEWS_SUPPORTED_LANGUAGES",
    "PerSecondLimiter",
    "Query",
    "QueryGenerator",
    "QueryResult",
    "SourceScheduler",
    "WindowLimiter",
    "batch_districts",
    "build_broad_query",
    "build_category_query",
    "create_gnews_scheduler",
    "create_google_scheduler",
    "create_newsdata_scheduler",
]
