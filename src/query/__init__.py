"""Query engine for the heat news extraction pipeline.

The query engine package provides the complete query lifecycle:

- **Data models** (:mod:`._models`): ``Query`` and ``QueryResult`` frozen
  dataclasses, plus query string construction helpers (``build_category_query``,
  ``build_broad_query``, ``batch_districts``).
- **Generator** (:mod:`._generator`): ``QueryGenerator`` combines heat terms
  with geographic data to produce API-ready search queries for Google News,
  NewsData.io, and GNews at both state and district levels.
- **Scheduler** (:mod:`._scheduler`): ``SourceScheduler`` wraps any
  ``NewsSource`` with daily budgets, rolling-window rate limiting, per-second
  delays, and concurrency control.  Factory functions create pre-configured
  schedulers for each source.
- **Executor** (:mod:`._executor`): ``QueryExecutor`` orchestrates hierarchical
  state-then-district execution across all sources in parallel via
  ``asyncio.TaskGroup``.
"""

from ._executor import QueryExecutor
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
    "QueryExecutor",
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
