"""QueryExecutor -- orchestrates hierarchical state-then-district query execution.

Ties together the QueryGenerator (what to search) with SourceSchedulers
(how to search safely) into a two-phase hierarchical execution flow:

1. **Phase 1 -- State-level queries:** Execute across all sources in parallel.
2. **Phase 2 -- District-level queries:** Only for states that returned results,
   only through sources that still have remaining budget.

All three sources execute concurrently via ``asyncio.TaskGroup``.  Errors are
caught and logged -- ``run_collection`` never raises.
"""

from __future__ import annotations

import asyncio
import logging

from src.data.geo_loader import StateUT, get_all_regions
from src.models.article import ArticleRef

from ._generator import QueryGenerator
from ._models import Query, QueryResult
from ._scheduler import SourceScheduler

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Orchestrates hierarchical query execution across multiple news sources.

    Constructor:
        schedulers: dict keyed by source name ("google", "newsdata", "gnews"),
            each value a SourceScheduler wrapping a NewsSource.
        generator: QueryGenerator that produces Query objects from geographic
            data and heat terms.
    """

    def __init__(
        self,
        schedulers: dict[str, SourceScheduler],
        generator: QueryGenerator,
    ) -> None:
        self._schedulers = schedulers
        self._generator = generator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_collection(
        self, regions: list[StateUT] | None = None
    ) -> list[ArticleRef]:
        """Run hierarchical state-then-district collection.

        Args:
            regions: List of states/UTs to query.  If ``None``, loads all
                regions via :func:`get_all_regions`.

        Returns:
            Flat list of all :class:`ArticleRef` objects collected across
            both phases and all sources.
        """
        if regions is None:
            regions = get_all_regions()

        all_articles: list[ArticleRef] = []

        # ----------------------------------------------------------
        # Phase 1 -- State-level queries
        # ----------------------------------------------------------
        logger.info("Phase 1: generating state-level queries for %d regions", len(regions))
        queries_by_source = self._generator.generate_state_queries(regions)

        for source_key, queries in queries_by_source.items():
            logger.info("  %s: %d state queries", source_key, len(queries))

        state_results = await self._execute_queries_parallel(queries_by_source)

        # Collect articles from state results
        for result in state_results:
            all_articles.extend(result.articles)

        state_article_count = len(all_articles)
        logger.info(
            "Phase 1 complete: %d articles from %d query results",
            state_article_count,
            len(state_results),
        )

        # ----------------------------------------------------------
        # Determine active states (states that returned articles)
        # ----------------------------------------------------------
        active_slugs: set[str] = set()
        for result in state_results:
            if result.articles:
                active_slugs.add(result.query.state_slug)

        logger.info(
            "%d / %d states have active heat news",
            len(active_slugs),
            len(regions),
        )

        # ----------------------------------------------------------
        # Phase 2 -- District-level queries (active states only)
        # ----------------------------------------------------------
        active_regions = [r for r in regions if r.slug in active_slugs]

        if not active_regions:
            logger.info("Phase 2: skipping district queries -- no active states")
        else:
            logger.info(
                "Phase 2: generating district queries for %d active states",
                len(active_regions),
            )

            district_queries_by_source: dict[str, list[Query]] = {}

            for hint, scheduler in self._schedulers.items():
                budget = scheduler.remaining_budget
                if budget is not None and budget <= 0:
                    logger.info("  %s: budget exhausted, skipping district queries", hint)
                    continue
                district_qs = self._generator.generate_district_queries(
                    active_regions, source_hint=hint  # type: ignore[arg-type]
                )
                if district_qs:
                    district_queries_by_source[hint] = district_qs
                    logger.info("  %s: %d district queries", hint, len(district_qs))

            if district_queries_by_source:
                district_results = await self._execute_queries_parallel(
                    district_queries_by_source
                )
                for result in district_results:
                    all_articles.extend(result.articles)

        total = len(all_articles)
        logger.info(
            "Collection complete: %d total articles from %d state + %d district",
            total,
            state_article_count,
            total - state_article_count,
        )

        return all_articles

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_queries_parallel(
        self, queries_by_source: dict[str, list[Query]]
    ) -> list[QueryResult]:
        """Execute queries for each source in parallel via ``asyncio.TaskGroup``.

        Each source processes its queries sequentially through
        :meth:`_execute_query_list` (the scheduler handles internal rate
        limiting and concurrency).  Sources run concurrently.

        Wraps the TaskGroup in ``try/except*`` to handle ExceptionGroups
        without crashing -- logs all exceptions and returns whatever
        results were collected.
        """
        results: list[QueryResult] = []

        async def _run_source(source_key: str, source_queries: list[Query]) -> None:
            scheduler = self._schedulers.get(source_key)
            if scheduler is None:
                logger.warning(
                    "No scheduler registered for source '%s', skipping %d queries",
                    source_key,
                    len(source_queries),
                )
                return
            source_results = await self._execute_query_list(scheduler, source_queries)
            results.extend(source_results)

        try:
            async with asyncio.TaskGroup() as tg:
                for source_key, source_queries in queries_by_source.items():
                    tg.create_task(_run_source(source_key, source_queries))
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error(
                    "Error during parallel query execution: %s",
                    exc,
                    exc_info=exc,
                )

        return results

    async def _execute_query_list(
        self, scheduler: SourceScheduler, queries: list[Query]
    ) -> list[QueryResult]:
        """Run a list of queries through a single scheduler sequentially.

        Checks remaining budget after each query and breaks early if
        the scheduler's budget is exhausted.

        Returns:
            List of QueryResult objects from executing the queries.
        """
        results: list[QueryResult] = []
        for query in queries:
            result = await scheduler.execute(query)
            results.append(result)

            # Break early if budget exhausted
            budget = scheduler.remaining_budget
            if budget is not None and budget <= 0:
                logger.info(
                    "%s: budget exhausted after %d/%d queries, stopping",
                    scheduler.name,
                    len(results),
                    len(queries),
                )
                break

        return results
